"""pywebview アプリケーションのエントリポイント。"""

import os
import socket
import threading
import time

import uvicorn
import webview
from webview import Window
from webview.menu import Menu, MenuAction

from backend import paths, state_store
from backend.services import update_service
from backend.state_store import WindowState

# アプリモードを宣言してからバックエンドをインポートさせる（ログレベルが INFO になる）
# uvicorn.run は文字列で "backend.main:app" を受けるので実行時まで main はインポートされない
os.environ.setdefault("GIT_LANES_MODE", "app")

HOST = "127.0.0.1"

_save_timer: threading.Timer | None = None
_timer_lock = threading.Lock()
_update_win: Window | None = None


def _find_free_port() -> int:
    """OS に空きポートを割り当ててもらう。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _start_server(port: int) -> None:
    """バックグラウンドスレッドで uvicorn を起動する。"""
    uvicorn.run("backend.main:app", host=HOST, port=port, log_level="warning")


def _wait_for_server(port: int, timeout: float = 10.0) -> bool:
    """サーバーが応答するまで待機する。

    Args:
        port: 待機するポート番号。
        timeout: 最大待機秒数。

    Returns:
        サーバーが起動したら True、タイムアウトなら False。
    """
    import urllib.request

    url = f"http://{HOST}:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _build_initial_url(port: int, state: WindowState) -> str:
    """保存済み状態から初期 URL を構築する。

    Args:
        port: FastAPI が Listen しているポート番号。
        state: 保存済みウィンドウ状態。

    Returns:
        webview.create_window() に渡す URL 文字列。
    """
    if state.repo_id is None:
        return f"http://{HOST}:{port}/"
    remote = str(state.show_remote).lower()
    tags = str(state.show_tags).lower()
    url = f"http://{HOST}:{port}/repos/{state.repo_id}/graph?show_remote={remote}&show_tags={tags}"
    if state.commit_hash:
        url += f"&active_commit={state.commit_hash}"
    return url


def _open_update_dialog(port: int) -> None:
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


def _schedule_save(path: object, state: WindowState) -> None:
    """デバウンスしてウィンドウ状態を保存する（500ms 後に書き込み）。"""
    global _save_timer
    with _timer_lock:
        if _save_timer is not None:
            _save_timer.cancel()
        _save_timer = threading.Timer(0.5, state_store.save, (path, state))
        _save_timer.daemon = True
        _save_timer.start()


def _register_window_events(win: Window, path: object, state: WindowState) -> None:
    """pywebview ウィンドウのイベントハンドラーを登録する。

    Args:
        win: pywebview ウィンドウオブジェクト。
        path: window_state.json のパス。
        state: 更新対象の WindowState オブジェクト。
    """

    def on_moved(x: int, y: int) -> None:
        state.x = int(x)
        state.y = int(y)
        _schedule_save(path, state)

    def on_resized(width: int, height: int) -> None:
        state.width = int(width)
        state.height = int(height)
        _schedule_save(path, state)

    win.events.moved += on_moved
    win.events.resized += on_resized


def main() -> None:
    """pywebview アプリを起動する。"""
    path = paths.window_state_path()
    state = state_store.load(path)

    port = _find_free_port()
    menu = [
        Menu(
            "Git Lanes",
            [
                MenuAction(
                    "Check for Updates...",
                    lambda: _open_update_dialog(port),
                ),
            ],
        )
    ]
    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()

    if not _wait_for_server(port):
        raise RuntimeError("サーバーの起動がタイムアウトしました。")

    win = webview.create_window(
        title="Git Lanes",
        url=_build_initial_url(port, state),
        width=state.width,
        height=state.height,
        x=state.x,
        y=state.y,
        resizable=True,
    )

    if win is None:
        raise RuntimeError("ウィンドウの作成に失敗しました。")

    _register_window_events(win, path, state)
    webview.start(menu=menu)

    # ウィンドウが閉じられたら保留中の debounce タイマーをキャンセルして即座に保存する
    # daemon=True のタイマーはプロセス終了と同時に強制停止されるため、ここで同期保存する
    with _timer_lock:
        if _save_timer is not None:
            _save_timer.cancel()
    state_store.save(path, state)


if __name__ == "__main__":
    main()
