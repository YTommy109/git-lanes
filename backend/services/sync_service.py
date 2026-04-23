"""Git リポジトリから SQLite キャッシュへ同期する。"""

from __future__ import annotations

import sqlite3

import pygit2

from backend.repositories import cache_read, cache_write
from backend.repositories.git_repo import (
    iter_local_branches,
    open_repository,
    walk_commits_from_head,
)


def _head_hex_or_none(repo: pygit2.Repository) -> str | None:
    try:
        return str(repo.head.target)
    except (KeyError, pygit2.GitError):
        return None


def _should_resync(conn: sqlite3.Connection, repo_id: str, head_hex: str | None) -> bool:
    if cache_read.get_repository(conn, repo_id) is None:
        return False
    if head_hex is None:
        return True
    if cache_read.count_commits(conn, repo_id) == 0:
        return True
    rec = cache_read.get_repository(conn, repo_id)
    assert rec is not None
    return rec.cached_head != head_hex


def sync_repository(conn: sqlite3.Connection, repo_id: str, repo_path: str) -> None:
    """必要ならリポジトリ内容をフル再同期する。

    HEAD が前回同期時と同じでコミットが残っていれば何もしない。

    Args:
        conn: SQLite 接続。
        repo_id: リポジトリ ID。
        repo_path: Git 作業コピーのパス。
    """
    repo = open_repository(repo_path)
    head_hex = _head_hex_or_none(repo)
    if not _should_resync(conn, repo_id, head_hex):
        return
    cache_write.purge_graph_data(conn, repo_id)
    if head_hex is None:
        cache_write.update_sync_state(conn, repo_id, None)
        return
    commits = walk_commits_from_head(repo)
    for c in commits:
        message_line = c.message.split("\n", 1)[0]
        cid = str(c.id)
        cache_write.insert_commit_row(
            conn,
            repo_id,
            cid,
            cid[:7],
            message_line,
            c.author.name,
            c.author.email,
            int(c.commit_time),
        )
    for c in commits:
        for pos, parent_id in enumerate(c.parent_ids):
            cache_write.insert_parent_row(conn, str(c.id), str(parent_id), pos)
    try:
        for branch_name, tip in iter_local_branches(repo):
            cache_write.insert_branch_row(conn, repo_id, branch_name, tip, 0)
    except pygit2.GitError:
        pass
    conn.commit()
    cache_write.update_sync_state(conn, repo_id, head_hex)
