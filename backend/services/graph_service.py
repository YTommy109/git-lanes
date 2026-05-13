"""グラフデータの同期・構築サービス。"""

from __future__ import annotations

import logging

import pygit2
from sqlmodel import Session

from backend.exceptions import GitOpenError
from backend.repositories import branch_repo, commit_repo, tag_repo
from backend.services import grid_builder, sync_service
from backend.services.branch_filter import categorize_branches
from backend.services.fork_point import compute_fork_data, persist_fork_points
from backend.services.graph_models import GraphResult

_logger = logging.getLogger(__name__)


def sync_and_build(
    session: Session,
    repo_id: str,
    repo_path: str,
    show_remote: bool = True,
    show_tags: bool = True,
) -> GraphResult:
    """リポジトリを同期してグラフデータを構築する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo_path: Git 作業コピーのパス。
        show_remote: False のときリモートブランチを全除外する。
        show_tags: False のときタグラベルを表示しない。

    Returns:
        SVG テンプレートへ渡す GraphResult。

    Raises:
        GitOpenError: Git リポジトリを開けない場合。
    """
    try:
        sync_service.sync_repository(session, repo_id, repo_path)
    except pygit2.GitError as exc:
        raise GitOpenError from exc
    rows = commit_repo.list_all_commits(session, repo_id)
    parents = commit_repo.parents_by_child(session, [r.hash for r in rows])
    cats = categorize_branches(branch_repo.list_branches(session, repo_id))
    label_only = cats.synced_remotes if show_remote else []
    branches = cats.local + (cats.diverged_remotes if show_remote else [])
    tags = tag_repo.list_tags(session, repo_id) if show_tags else []
    _logger.debug(
        "グラフ描画: repo_id=%s commits=%d branches=%d", repo_id, len(rows), len(branches)
    )
    fork_data = compute_fork_data(rows, parents, branches)
    persist_fork_points(session, branches, fork_data)
    return grid_builder.build_grid(
        rows, parents, branches, tags, fork_data, label_only_branches=label_only
    )
