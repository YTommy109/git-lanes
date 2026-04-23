"""E2E テスト用 fixture。FastAPI サーバーをサブプロセスで起動する。"""
import subprocess
import time
import urllib.error
import urllib.request

import pytest


@pytest.fixture(scope="session")
def _server():
    """テストセッション中 FastAPI サーバーをポート 8001 で起動する。"""
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "backend.main:app", "--port", "8001"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # サーバーが応答するまで最大 10 秒待機する
    for _ in range(20):
        try:
            urllib.request.urlopen("http://localhost:8001/health", timeout=1)
            break
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    yield
    proc.terminate()
    proc.wait()


@pytest.fixture
def base_url(_server: None) -> str:
    return "http://localhost:8001"
