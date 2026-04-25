"""pywebview アプリケーションのエントリポイント。"""

import socket
import threading
import time

import uvicorn
import webview

HOST = "127.0.0.1"


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


def main() -> None:
    """pywebview アプリを起動する。"""
    port = _find_free_port()
    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()

    if not _wait_for_server(port):
        raise RuntimeError("サーバーの起動がタイムアウトしました。")

    webview.create_window(
        title="Git Lanes",
        url=f"http://{HOST}:{port}/",
        width=1280,
        height=800,
        resizable=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
