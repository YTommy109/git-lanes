"""pywebview アプリケーションのエントリポイント。"""

import threading
import time

import uvicorn
import webview

HOST = "127.0.0.1"
PORT = 8765


def _start_server() -> None:
    """バックグラウンドスレッドで uvicorn を起動する。"""
    uvicorn.run("backend.main:app", host=HOST, port=PORT, log_level="warning")


def _wait_for_server(timeout: float = 10.0) -> bool:
    """サーバーが応答するまで待機する。

    Args:
        timeout: 最大待機秒数。

    Returns:
        サーバーが起動したら True、タイムアウトなら False。
    """
    import urllib.request

    url = f"http://{HOST}:{PORT}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def main() -> None:
    """pywebview アプリを起動する。"""
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    if not _wait_for_server():
        raise RuntimeError("サーバーの起動がタイムアウトしました。")

    webview.create_window(
        title="Git Lanes",
        url=f"http://{HOST}:{PORT}/",
        width=1280,
        height=800,
        resizable=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
