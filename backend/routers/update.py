# backend/routers/update.py
"""アップデート確認・ダウンロード・インストールの API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.services import update_service
from backend.services.update_installer import install_update

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
router = APIRouter(prefix="/api/update", tags=["update"])


@router.get("/check", response_class=HTMLResponse)
def check_update(request: Request) -> HTMLResponse:
    """更新確認。更新がなければ空レスポンスを返す。"""
    result = update_service.check_update()
    if not result["available"]:
        return HTMLResponse(content="")
    return templates.TemplateResponse(
        request,
        "partials/update_banner.html",
        {"version": result["version"], "download_url": result["download_url"]},
    )


@router.post("/download", response_class=HTMLResponse)
def start_download(request: Request) -> HTMLResponse:
    """ダウンロードを開始し、進捗 UI を返す。"""
    result = update_service.check_update()
    if result["download_url"]:
        update_service.download_update(result["download_url"])
    state = update_service.get_download_state()
    return templates.TemplateResponse(
        request,
        "partials/update_progress.html",
        {"percent": state["percent"], "status": state["status"]},
    )


@router.get("/progress", response_class=HTMLResponse)
def get_progress(request: Request) -> HTMLResponse:
    """ダウンロード進捗 HTML を返す（1秒ポーリング用）。"""
    state = update_service.get_download_state()
    return templates.TemplateResponse(
        request,
        "partials/update_progress.html",
        {"percent": state["percent"], "status": state["status"]},
    )


@router.post("/install")
def do_install() -> None:
    """インストールして再起動する。"""
    install_update()
