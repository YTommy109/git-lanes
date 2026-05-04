"""watchdog → SQLite 更新 → EventBus.notify() までの結合テスト。"""

from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock

import pygit2
import pytest
from sqlalchemy import create_engine
from sqlalchemy import event as sqla_event
from sqlmodel import Session, SQLModel

import backend.models  # noqa: F401 — テーブル登録のため必要
from backend.repositories import commit_repo, repository_repo
from backend.services import sync_service
from backend.services.event_bus import EventBus
from backend.services.watch_service import WatchService
from tests.support.git_repo_fixture import make_two_commit_repo


@pytest.fixture()
def watch_engine(tmp_path):
    """WatchService テスト用の独立した SQLite エンジンを返す。"""
    eng = create_engine(
        f"sqlite:///{tmp_path}/watch_test.db",
        connect_args={"check_same_thread": False},
    )

    @sqla_event.listens_for(eng, "connect")
    def _pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(eng)
    return eng


def _make_commit(repo_path, message: str) -> None:
    """テスト用リポジトリに新しいコミットを追加する。"""
    repo = pygit2.Repository(str(repo_path))
    sig = pygit2.Signature("テスト", "t@example.com", int(time.time()), 0)
    (repo_path / f"{message}.txt").write_text(message, encoding="utf-8")
    repo.index.read()
    repo.index.add(f"{message}.txt")
    repo.index.write()
    tree = repo.index.write_tree()
    repo.create_commit("HEAD", sig, sig, message, tree, [repo.head.target])


def test_コミット後にwatchdogがnotifyを呼ぶ(tmp_path, watch_engine):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())

    with Session(watch_engine) as session:
        repository_repo.insert_repository(session, repo_id, str(repo_path), "repo")
        sync_service.sync_repository(session, repo_id, str(repo_path))

    bus = MagicMock(spec=EventBus)
    svc = WatchService(bus, watch_engine)
    svc.watch(repo_id, str(repo_path))
    svc.start()
    time.sleep(0.1)  # Observer 起動待ち

    # --- Act ---
    _make_commit(repo_path, "third")
    time.sleep(1.5)  # デバウンス (0.5s) + 同期処理待ち

    svc.stop()

    # --- Assert ---
    bus.notify.assert_called_with(repo_id)


def test_コミット後にSQLiteが更新される(tmp_path, watch_engine):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())

    with Session(watch_engine) as session:
        repository_repo.insert_repository(session, repo_id, str(repo_path), "repo")
        sync_service.sync_repository(session, repo_id, str(repo_path))
        count_before = commit_repo.count_commits(session, repo_id)

    bus = MagicMock(spec=EventBus)
    svc = WatchService(bus, watch_engine)
    svc.watch(repo_id, str(repo_path))
    svc.start()
    time.sleep(0.1)

    # --- Act ---
    _make_commit(repo_path, "third")
    time.sleep(1.5)

    svc.stop()

    # --- Assert ---
    with Session(watch_engine) as session:
        count_after = commit_repo.count_commits(session, repo_id)
    assert count_after == count_before + 1
