"""E2E テスト用 fixture。FastAPI サーバーをサブプロセスで起動する。"""

import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def git_lanes_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """SQLite を置くディレクトリ（セッション単位）。"""
    return tmp_path_factory.mktemp("git_lanes_data")


@pytest.fixture(scope="session")
def _server(git_lanes_data_dir: Path):
    """テストセッション中 FastAPI サーバーをポート 8001 で起動する。"""
    env = os.environ.copy()
    env["GIT_LANES_DATA_DIR"] = str(git_lanes_data_dir)
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "backend.main:app", "--port", "8001"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
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


@pytest.fixture(scope="session")
def base_url(_server: None) -> str:
    return "http://localhost:8001"
