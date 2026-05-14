"""更新確認ダイアログウィンドウの管理。"""

from __future__ import annotations

import webview
from webview.menu import Menu, MenuAction  # noqa: F401

from backend.services import update_service

_update_win: webview.Window | None = None

HOST = "127.0.0.1"


def open_update_dialog(port: int) -> None:
    """更新確認ダイアログを開く。すでに開いていれば何もしない。

    Args:
        port: FastAPI が Listen しているポート番号。
    """
    global _update_win
    if _update_win is not None:
        return
    update_service.invalidate_cache()
    url = f"http://{HOST}:{port}/api/update/dialog"
    win = webview.create_window(
        title="アップデート確認",
        url=url,
        width=400,
        height=260,
        resizable=False,
    )
    if win is None:
        return

    def _on_closed() -> None:
        global _update_win
        _update_win = None

    win.events.closed += _on_closed
    _update_win = win
