# backend/main.py
"""FastAPI アプリケーションのエントリポイント。"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from backend.db import create_db_and_tables, engine
from backend.logging_config import get_log_path, setup_logging
from backend.repositories import cache_repo
from backend.routers import api, html, update
from backend.routers.graph_events import make_router
from backend.services.event_bus import event_bus
from backend.services.watch_service import WatchService

ROOT = Path(__file__).resolve().parent.parent
# GIT_LANES_MODE=app のとき本番モード（INFO）、未設定は開発モード（DEBUG）
_debug = os.environ.get("GIT_LANES_MODE") != "app"
setup_logging(debug=_debug)
_logger = logging.getLogger(__name__)
_logger.info("Git Lanes 起動: mode=%s log=%s", "dev" if _debug else "app", get_log_path())


def _start_watch_service(app: FastAPI) -> WatchService:
    """既存リポジトリを全て監視する WatchService を起動する。"""
    loop = asyncio.get_running_loop()
    event_bus.set_loop(loop)
    watch_svc = WatchService(event_bus, engine)
    with Session(engine) as session:
        for repo in cache_repo.list_repositories(session):
            watch_svc.watch(repo.id, repo.path)
    watch_svc.start()
    app.state.watch_service = watch_svc
    return watch_svc


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時にテーブル作成と監視サービスを起動する。"""
    create_db_and_tables()
    watch_svc = _start_watch_service(app)
    yield
    watch_svc.stop()


app = FastAPI(title="Git Lanes", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.include_router(html.router)
app.include_router(api.router)
app.include_router(update.router)
app.include_router(make_router(event_bus))


@app.get("/health")
async def health_check() -> dict[str, str]:
    """サーバーの稼働確認用エンドポイント。"""
    return {"status": "ok"}
