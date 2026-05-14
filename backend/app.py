"""pywebview アプリケーションのエントリポイント。"""

import os
import threading

import webview
from webview import Window

from backend import paths, state_store
from backend.server import find_free_port, start_server, wait_for_server
from backend.state_store import WindowState
from backend.update_window import Menu, MenuAction, open_update_dialog

# アプリモードを宣言してからバックエンドをインポートさせる（ログレベルが INFO になる）
# uvicorn.run は文字列で "backend.main:app" を受けるので実行時まで main はインポートされない
os.environ.setdefault("GIT_LANES_MODE", "app")

HOST = "127.0.0.1"

_save_timer: threading.Timer | None = None
_timer_lock = threading.Lock()


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

    port = find_free_port()
    menu = [
        Menu(
            "Git Lanes",
            [
                MenuAction(
                    "Check for Updates...",
                    lambda: open_update_dialog(port),
                ),
            ],
        )
    ]
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    if not wait_for_server(port):
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
