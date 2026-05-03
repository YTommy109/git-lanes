"""Git リポジトリから SQLite キャッシュへ同期する。"""

from __future__ import annotations

import logging

import pygit2
from sqlmodel import Session

from backend.repositories import cache_repo
from backend.repositories.git_repo import (
    iter_local_branches,
    iter_remote_branches,
    iter_tags,
    open_repository,
    walk_commits_from_branches,
)

_logger = logging.getLogger(__name__)


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


def _has_missing_tips(session: Session, repo_id: str, repo: pygit2.Repository) -> bool:
    """ローカル・リモートのブランチ先端コミットが DB に未収録なら True を返す。"""
    for _, tip in (*iter_local_branches(repo), *iter_remote_branches(repo)):
        if cache_repo.get_commit(session, repo_id, tip) is None:
            return True
    return False


def _has_missing_branches(session: Session, repo_id: str, repo: pygit2.Repository) -> bool:
    """DB に未登録のブランチが存在すれば True を返す。

    既存コミットを先端に持つ新ブランチ（git switch -c など）を検知する。
    """
    cached_names = {b.name for b in cache_repo.list_branches(session, repo_id)}
    all_names = [*repo.branches.local, *repo.branches.remote]
    return any(name not in cached_names for name in all_names)


def sync_repository(session: Session, repo_id: str, repo_path: str) -> None:
    """必要ならリポジトリ内容をフル再同期する。

    HEAD が変わらなくても未収録のブランチ先端コミットがあれば再同期する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo_path: Git 作業コピーのパス。
    """
    repo = open_repository(repo_path)
    head_hex = _head_hex_or_none(repo)
    needs_sync = (
        _should_resync(session, repo_id, head_hex)
        or _has_missing_tips(session, repo_id, repo)
        or _has_missing_branches(session, repo_id, repo)
    )
    if not needs_sync:
        return
    cache_repo.purge_graph_data(session, repo_id)
    if head_hex is None:
        cache_repo.update_sync_state(session, repo_id, None)
        return
    _sync_commits_and_branches(session, repo_id, repo, head_hex)


def _sync_tags(session: Session, repo_id: str, repo: pygit2.Repository) -> None:
    """ウォークツリー内のタグをキャッシュに書き込む。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo: pygit2 リポジトリ。
    """
    for tag_name, commit_hash in iter_tags(repo):
        if cache_repo.get_commit(session, repo_id, commit_hash) is not None:
            cache_repo.insert_tag_row(session, repo_id, tag_name, commit_hash)


def _sync_parents(session: Session, commits: list) -> None:
    """コミットの親子関係をキャッシュに書き込む。

    Args:
        session: DB セッション。
        commits: pygit2.Commit のリスト。
    """
    for c in commits:
        for pos, parent_id in enumerate(c.parent_ids):
            cache_repo.insert_parent_row(session, str(c.id), str(parent_id), pos)


def _sync_commits_and_branches(
    session: Session,
    repo_id: str,
    repo: pygit2.Repository,
    head_hex: str,
) -> None:
    """コミット・ブランチ・タグをキャッシュに書き込む。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo: pygit2 リポジトリ。
        head_hex: 現在の HEAD ハッシュ。
    """
    commits = walk_commits_from_branches(repo)
    _logger.info("同期実行: repo_id=%s commits=%d", repo_id, len(commits))
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
    _sync_parents(session, commits)
    try:
        for branch_name, tip in iter_local_branches(repo):
            cache_repo.insert_branch_row(session, repo_id, branch_name, tip, 0)
        for branch_name, tip in iter_remote_branches(repo):
            cache_repo.insert_branch_row(session, repo_id, branch_name, tip, 1)
    except pygit2.GitError:
        pass
    _sync_tags(session, repo_id, repo)
    session.commit()
    cache_repo.update_sync_state(session, repo_id, head_hex)
