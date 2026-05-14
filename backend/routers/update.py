# backend/routers/update.py
"""アップデート確認・ダウンロード・インストールの API。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from backend.jinja import templates
from backend.services import update_service
from backend.services.update_installer import install_update
from backend.version import __version__ as _CURRENT_VERSION

router = APIRouter(prefix="/api/update", tags=["update"])


@router.get("/dialog", response_class=HTMLResponse)
def update_dialog(request: Request) -> HTMLResponse:
    """更新確認ダイアログ用ページを返す。"""
    result = update_service.check_update()
    return templates.TemplateResponse(
        request,
        "update_dialog.html",
        {
            "available": result["available"],
            "latest_version": result["version"],
            "current_version": _CURRENT_VERSION,
            "download_url": result["download_url"],
        },
    )


@router.get("/check", response_class=HTMLResponse)
def check_update(request: Request) -> HTMLResponse:
    """更新確認。更新がなければアイドル div を返す。"""
    result = update_service.check_update()
    if not result["available"]:
        return templates.TemplateResponse(
            request,
            "partials/update_idle.html",
            {},
        )
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


@router.post("/install", response_class=HTMLResponse)
def do_install(request: Request) -> HTMLResponse:
    """インストールして再起動する。エラー時はエラー状態の UI を返す。"""
    result = install_update()
    # "not_frozen" は開発環境なので正常扱い（UI テスト用）
    if result in ("not_frozen",):
        return HTMLResponse(content="")
    state = {"percent": 100, "status": f"install_error:{result}"}
    return templates.TemplateResponse(
        request,
        "partials/update_progress.html",
        {"percent": 100, "status": state["status"]},
    )
