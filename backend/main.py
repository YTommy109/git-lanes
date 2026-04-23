"""FastAPI アプリケーションのエントリポイント。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routers import api, html

ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="Git Lanes")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.include_router(html.router)
app.include_router(api.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """サーバーの稼働確認用エンドポイント。"""
    return {"status": "ok"}
