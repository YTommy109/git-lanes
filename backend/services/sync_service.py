"""Git リポジトリから SQLite キャッシュへ同期する。"""

from __future__ import annotations

import pygit2
from sqlmodel import Session

from backend.repositories import cache_repo
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


def _should_resync(session: Session, repo_id: str, head_hex: str | None) -> bool:
    if cache_repo.get_repository(session, repo_id) is None:
        return False
    if head_hex is None:
        return True
    if cache_repo.count_commits(session, repo_id) == 0:
        return True
    rec = cache_repo.get_repository(session, repo_id)
    assert rec is not None
    return rec.cached_head != head_hex


def sync_repository(session: Session, repo_id: str, repo_path: str) -> None:
    """必要ならリポジトリ内容をフル再同期する。

    HEAD が前回同期時と同じでコミットが残っていれば何もしない。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo_path: Git 作業コピーのパス。
    """
    repo = open_repository(repo_path)
    head_hex = _head_hex_or_none(repo)
    if not _should_resync(session, repo_id, head_hex):
        return
    cache_repo.purge_graph_data(session, repo_id)
    if head_hex is None:
        cache_repo.update_sync_state(session, repo_id, None)
        return
    _sync_commits_and_branches(session, repo_id, repo, head_hex)


def _sync_commits_and_branches(
    session: Session,
    repo_id: str,
    repo: pygit2.Repository,
    head_hex: str,
) -> None:
    """コミット・ブランチをキャッシュに書き込む。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo: pygit2 リポジトリ。
        head_hex: 現在の HEAD ハッシュ。
    """
    commits = walk_commits_from_head(repo)
    # 親ハッシュへの外部キー制約を満たすため、コミットを先に全件挿入する。
    for c in commits:
        message_line = c.message.split("\n", 1)[0]
        cid = str(c.id)
        cache_repo.insert_commit_row(
            session,
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
            cache_repo.insert_parent_row(session, str(c.id), str(parent_id), pos)
    try:
        for branch_name, tip in iter_local_branches(repo):
            cache_repo.insert_branch_row(session, repo_id, branch_name, tip, 0)
    except pygit2.GitError:
        pass
    session.commit()
    cache_repo.update_sync_state(session, repo_id, head_hex)
