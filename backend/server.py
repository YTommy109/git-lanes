"""FastAPI サブプロセスの起動・待機ユーティリティ。"""

from __future__ import annotations

import socket
import time
import urllib.request

import uvicorn

HOST = "127.0.0.1"


def find_free_port() -> int:
    """OS に空きポートを割り当ててもらう。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def start_server(port: int) -> None:
    """バックグラウンドスレッドで uvicorn を起動する。"""
    uvicorn.run("backend.main:app", host=HOST, port=port, log_level="warning")


def wait_for_server(port: int, timeout: float = 10.0) -> bool:
    """サーバーが応答するまで待機する。

    Args:
        port: 待機するポート番号。
        timeout: 最大待機秒数。

    Returns:
        サーバーが起動したら True、タイムアウトなら False。
    """
    url = f"http://{HOST}:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False
