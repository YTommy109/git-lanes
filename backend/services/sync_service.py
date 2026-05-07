"""Git リポジトリから SQLite キャッシュへ同期する。"""

from __future__ import annotations

import logging

import pygit2
from sqlmodel import Session

from backend.repositories import branch_repo, commit_repo, repository_repo, tag_repo
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
    rec = repository_repo.get_repository(session, repo_id)
    if rec is None:
        return False
    if head_hex is None:
        return True
    if commit_repo.count_commits(session, repo_id) == 0:
        return True
    return rec.cached_head != head_hex


def _has_change_to_sync(session: Session, repo_id: str, repo: pygit2.Repository) -> bool:
    """コミット追加・ブランチ追加/削除が未収録なら True を返す。

    先端コミットの未収録、DB に存在しないブランチ、git に存在しないブランチをまとめて検知する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo: pygit2 リポジトリ。

    Returns:
        再同期が必要なら True。
    """
    branches = [*iter_local_branches(repo), *iter_remote_branches(repo)]
    for _, tip in branches:
        if commit_repo.get_commit(session, repo_id, tip) is None:
            return True
    cached = {b.name for b in branch_repo.list_branches(session, repo_id)}
    current = {name for name, _ in branches}
    return bool(current - cached) or bool(cached - current)


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
    needs_sync = _should_resync(session, repo_id, head_hex) or _has_change_to_sync(
        session, repo_id, repo
    )
    if not needs_sync:
        return
    repository_repo.purge_graph_data(session, repo_id)
    if head_hex is None:
        repository_repo.update_sync_state(session, repo_id, None)
        return
    _sync_commits_and_branches(session, repo_id, repo, head_hex)


def _sync_branches(session: Session, repo_id: str, repo: pygit2.Repository) -> None:
    """ローカル・リモートブランチをキャッシュに書き込む。"""
    try:
        for branch_name, tip in iter_local_branches(repo):
            branch_repo.insert_branch_row(session, repo_id, branch_name, tip, 0)
        for branch_name, tip in iter_remote_branches(repo):
            branch_repo.insert_branch_row(session, repo_id, branch_name, tip, 1)
    except pygit2.GitError:
        pass


def _sync_tags(session: Session, repo_id: str, repo: pygit2.Repository) -> None:
    """ウォークツリー内のタグをキャッシュに書き込む。"""
    for tag_name, commit_hash in iter_tags(repo):
        if commit_repo.get_commit(session, repo_id, commit_hash) is not None:
            tag_repo.insert_tag_row(session, repo_id, tag_name, commit_hash)


def _sync_parents(session: Session, commits: list) -> None:
    """コミットの親子関係をキャッシュに書き込む。"""
    for c in commits:
        for pos, parent_id in enumerate(c.parent_ids):
            commit_repo.insert_parent_row(session, str(c.id), str(parent_id), pos)


def _sync_commit_rows(session: Session, repo_id: str, commits: list) -> None:
    """コミット行を全件挿入する。"""
    # 親ハッシュへの外部キー制約を満たすため、コミットを先に全件挿入する。
    for c in commits:
        message_line = c.message.split("\n", 1)[0]
        cid = str(c.id)
        commit_repo.insert_commit_row(
            session,
            repo_id,
            cid,
            cid[:7],
            message_line,
            c.author.name,
            c.author.email,
            int(c.commit_time),
        )


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
    _sync_commit_rows(session, repo_id, commits)
    _sync_parents(session, commits)
    _sync_branches(session, repo_id, repo)
    _sync_tags(session, repo_id, repo)
    session.commit()
    repository_repo.update_sync_state(session, repo_id, head_hex)
