"""sync_service の単体テスト。"""

import uuid

import pygit2

from backend.repositories import cache_repo
from backend.services import sync_service
from tests.support.git_repo_fixture import make_two_commit_repo


def test_sync_repository_writes_commits(session, tmp_path):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    assert cache_repo.count_commits(session, repo_id) == 2
    rec = cache_repo.get_repository(session, repo_id)
    assert rec is not None
    assert rec.cached_head is not None


def test_sync_repository_handles_empty_repo(session, tmp_path):
    # --- Arrange ---
    repo_path = tmp_path / "empty"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "empty")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    assert cache_repo.count_commits(session, repo_id) == 0
