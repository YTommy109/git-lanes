"""sync_service の単体テスト。"""

import uuid
from contextlib import closing

import pygit2

from backend.paths import primary_db_path
from backend.repositories import cache_read, cache_write
from backend.services import sync_service
from tests.support.git_repo_fixture import make_two_commit_repo


def test_sync_repository_writes_commits(tmp_path, monkeypatch):
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    with closing(cache_read.connect(str(primary_db_path()))) as conn:
        cache_write.insert_repository(conn, repo_id, str(repo_path), "repo")

        # --- Act ---
        sync_service.sync_repository(conn, repo_id, str(repo_path))

        # --- Assert ---
        assert cache_read.count_commits(conn, repo_id) == 2
        rec = cache_read.get_repository(conn, repo_id)
        assert rec is not None
        assert rec.cached_head is not None


def test_sync_repository_handles_empty_repo(tmp_path, monkeypatch):
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))
    repo_path = tmp_path / "empty"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    repo_id = str(uuid.uuid4())
    with closing(cache_read.connect(str(primary_db_path()))) as conn:
        cache_write.insert_repository(conn, repo_id, str(repo_path), "empty")

        # --- Act ---
        sync_service.sync_repository(conn, repo_id, str(repo_path))

        # --- Assert ---
        assert cache_read.count_commits(conn, repo_id) == 0
