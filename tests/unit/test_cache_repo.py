"""cache_repo の単体テスト。"""

import time

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from backend.models import Branch, Commit, Repository
from backend.repositories import cache_repo

# ── ヘルパー ──────────────────────────────────────────────


def _add_repo(session: Session, repo_id: str = "r1") -> Repository:
    """テスト用リポジトリを登録して返す。"""
    cache_repo.insert_repository(session, repo_id, f"/path/{repo_id}", repo_id)
    repo = cache_repo.get_repository(session, repo_id)
    assert repo is not None
    return repo


def _add_commit(
    session: Session,
    repo_id: str,
    hash: str,
    committed_at: int = 1000,
) -> Commit:
    """テスト用コミットを挿入して返す。"""
    cache_repo.insert_commit_row(
        session, repo_id, hash, hash[:7], "msg", "author", "a@b.com", committed_at
    )
    commit = cache_repo.get_commit(session, repo_id, hash)
    assert commit is not None
    return commit


# ── get_repository ─────────────────────────────────────────


def test_get_repository_存在するIDを返す(session):
    # --- Arrange ---
    cache_repo.insert_repository(session, "r1", "/path/r1", "r1")

    # --- Act ---
    result = cache_repo.get_repository(session, "r1")

    # --- Assert ---
    assert result is not None
    assert result.id == "r1"
    assert result.path == "/path/r1"


def test_get_repository_存在しないIDはNoneを返す(session):
    # --- Act ---
    result = cache_repo.get_repository(session, "no-such-id")

    # --- Assert ---
    assert result is None


# ── count_commits ──────────────────────────────────────────


def test_count_commits_0件(session):
    # --- Arrange ---
    _add_repo(session)

    # --- Act & Assert ---
    assert cache_repo.count_commits(session, "r1") == 0


def test_count_commits_N件(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)

    # --- Act & Assert ---
    assert cache_repo.count_commits(session, "r1") == 2


# ── list_recent_commits ────────────────────────────────────


def test_list_recent_commits_committed_at降順(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40, committed_at=100)
    _add_commit(session, "r1", "b" * 40, committed_at=200)

    # --- Act ---
    rows = cache_repo.list_recent_commits(session, "r1", 10)

    # --- Assert ---
    assert [r.committed_at for r in rows] == [200, 100]


def test_list_recent_commits_limit超えは切り捨て(session):
    # --- Arrange ---
    _add_repo(session)
    for i in range(5):
        _add_commit(session, "r1", str(i) * 40, committed_at=i)

    # --- Act ---
    rows = cache_repo.list_recent_commits(session, "r1", 3)

    # --- Assert ---
    assert len(rows) == 3


# ── get_commit ─────────────────────────────────────────────


def test_get_commit_存在するコミットを返す(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)

    # --- Act ---
    result = cache_repo.get_commit(session, "r1", "a" * 40)

    # --- Assert ---
    assert result is not None
    assert result.hash == "a" * 40


def test_get_commit_存在しないはNoneを返す(session):
    # --- Arrange ---
    _add_repo(session)

    # --- Act ---
    result = cache_repo.get_commit(session, "r1", "z" * 40)

    # --- Assert ---
    assert result is None


# ── parents_by_child ───────────────────────────────────────


def test_parents_by_child_空リストは空dictを返す(session):
    # --- Act ---
    result = cache_repo.parents_by_child(session, [])

    # --- Assert ---
    assert result == {}


def test_parents_by_child_単親コミット(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)
    cache_repo.insert_parent_row(session, "b" * 40, "a" * 40, 0)
    session.commit()

    # --- Act ---
    result = cache_repo.parents_by_child(session, ["b" * 40])

    # --- Assert ---
    assert result == {"b" * 40: ["a" * 40]}


def test_parents_by_child_マージコミットはposition順(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)
    _add_commit(session, "r1", "c" * 40)
    cache_repo.insert_parent_row(session, "c" * 40, "a" * 40, 0)
    cache_repo.insert_parent_row(session, "c" * 40, "b" * 40, 1)
    session.commit()

    # --- Act ---
    result = cache_repo.parents_by_child(session, ["c" * 40])

    # --- Assert ---
    assert result == {"c" * 40: ["a" * 40, "b" * 40]}


# ── insert_repository ──────────────────────────────────────


def test_insert_repository_正常挿入(session):
    # --- Act ---
    cache_repo.insert_repository(session, "r1", "/path/r1", "repo1")

    # --- Assert ---
    rec = cache_repo.get_repository(session, "r1")
    assert rec is not None
    assert rec.name == "repo1"


def test_insert_repository_パス重複はIntegrityError(session):
    # --- Arrange ---
    cache_repo.insert_repository(session, "r1", "/path/same", "repo1")

    # --- Act & Assert ---
    with pytest.raises(IntegrityError):
        cache_repo.insert_repository(session, "r2", "/path/same", "repo2")


# ── purge_graph_data ───────────────────────────────────────


def test_purge_graph_data_commit_parents_branches_commitsが削除される(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)
    cache_repo.insert_parent_row(session, "b" * 40, "a" * 40, 0)
    cache_repo.insert_branch_row(session, "r1", "main", "b" * 40, 0)
    session.commit()

    # --- Act ---
    cache_repo.purge_graph_data(session, "r1")

    # --- Assert ---
    assert cache_repo.count_commits(session, "r1") == 0
    assert cache_repo.parents_by_child(session, ["b" * 40]) == {}


# ── update_sync_state ──────────────────────────────────────


def test_update_sync_state_cached_headとsynced_atが更新される(session):
    # --- Arrange ---
    _add_repo(session)
    before = int(time.time())

    # --- Act ---
    cache_repo.update_sync_state(session, "r1", "abc123")

    # --- Assert ---
    rec = cache_repo.get_repository(session, "r1")
    assert rec is not None
    assert rec.cached_head == "abc123"
    assert rec.synced_at is not None
    assert rec.synced_at >= before


# ── insert_commit_row（REPLACE） ───────────────────────────


def test_insert_commit_row_重複時はフィールドが更新される(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)

    # --- Act ---
    cache_repo.insert_commit_row(
        session, "r1", "a" * 40, "aaaaaaa", "updated msg", "new", "n@b.com", 9999
    )
    session.commit()

    # --- Assert ---
    rec = cache_repo.get_commit(session, "r1", "a" * 40)
    assert rec is not None
    assert rec.message == "updated msg"


# ── insert_branch_row（REPLACE） ───────────────────────────


def test_insert_branch_row_tip_hashが更新される(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)
    cache_repo.insert_branch_row(session, "r1", "main", "a" * 40, 0)
    session.commit()

    # --- Act ---
    cache_repo.insert_branch_row(session, "r1", "main", "b" * 40, 0)
    session.commit()

    # --- Assert ---
    branch = session.exec(
        select(Branch).where(Branch.name == "main", Branch.repo_id == "r1")
    ).first()
    assert branch is not None
    assert branch.tip_hash == "b" * 40
