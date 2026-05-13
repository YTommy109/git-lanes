"""html.py ハンドラーの状態保存テスト。"""

import time
from types import SimpleNamespace
from unittest.mock import ANY, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

import backend.models  # noqa: F401 — テーブル登録のため必要
from backend.db import get_session
from backend.main import app
from backend.models import Branch, Commit
from backend.repositories.repository_repo import insert_repository

REPO_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
COMMIT_HASH = "a" * 40


@pytest.fixture()
def client():
    """TestClient with in-memory DB（StaticPool でスレッド間共有）。"""
    # StaticPool: 同一接続をスレッド間で共有し、テーブルが見えるようにする
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        app.dependency_overrides[get_session] = lambda: session
        yield TestClient(app, raise_server_exceptions=False), session
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(client):
    """テスト用リポジトリとコミットを DB に挿入する。"""
    test_client, session = client
    insert_repository(session, REPO_ID, "/tmp/test-repo", "test-repo")
    session.add(
        Commit(
            hash=COMMIT_HASH,
            short_hash=COMMIT_HASH[:7],
            message="test commit",
            author_name="tester",
            author_email="t@t.com",
            committed_at=int(time.time()),
            repo_id=REPO_ID,
        )
    )
    session.add(Branch(name="main", repo_id=REPO_ID, tip_hash=COMMIT_HASH))
    session.commit()


def _dummy_graph():
    """graph_service.sync_and_build のダミー戻り値。"""
    return SimpleNamespace(
        nodes=[], edges=[], branch_headers=[], canvas_width=100, canvas_height=100
    )


def test_graph_page_はリポジトリ状態を保存する(client, seeded):
    """graph_page が state_store.update を呼んでリポジトリ状態を保存する。"""
    # --- Arrange ---
    test_client, _ = client
    with (
        patch("backend.routers.html.state_store.update") as mock_update,
        patch("backend.services.graph_service.sync_and_build", return_value=_dummy_graph()),
    ):
        # --- Act ---
        test_client.get(f"/repos/{REPO_ID}/graph?show_remote=true&show_tags=false")

    # --- Assert ---
    mock_update.assert_called_once_with(ANY, repo_id=REPO_ID, show_remote=True, show_tags=False)


def test_commit_detail_はコミットハッシュを保存する(client, seeded):
    """commit_detail が state_store.update を呼んでコミットハッシュを保存する。"""
    # --- Arrange ---
    test_client, _ = client
    with patch("backend.routers.html.state_store.update") as mock_update:
        # --- Act ---
        test_client.get(f"/repos/{REPO_ID}/commits/{COMMIT_HASH}/detail")

    # --- Assert ---
    mock_update.assert_called_once_with(ANY, commit_hash=COMMIT_HASH)


def test_graph_page_は_active_commit_で詳細パネルを描画する(client, seeded):
    """graph_page に active_commit を渡すと詳細パネルが初期描画される。"""
    # --- Arrange ---
    test_client, _ = client
    with (
        patch("backend.routers.html.state_store.update"),
        patch("backend.services.graph_service.sync_and_build", return_value=_dummy_graph()),
    ):
        # --- Act ---
        resp = test_client.get(f"/repos/{REPO_ID}/graph?active_commit={COMMIT_HASH}")

    # --- Assert ---
    assert resp.status_code == 200
    assert "test commit" in resp.text  # 詳細パネルにコミットメッセージが含まれる
