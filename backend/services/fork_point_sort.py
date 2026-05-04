"""ブランチのソートと DB 永続化ユーティリティ。"""

from __future__ import annotations

from sqlmodel import Session

from backend.models import Branch
from backend.services.fork_point import ForkData


def sort_branches_by_fork_data(
    branches: list[Branch],
    fork_data: dict[str, ForkData],
) -> list[Branch]:
    """フォークポイントの新しい順（None は最右）にブランチを並べる。

    Args:
        branches: ブランチリスト。
        fork_data: ブランチ名 → ForkData のマップ。

    Returns:
        ソート済みブランチリスト。
    """

    def _key(b: Branch) -> tuple[int, int]:
        data = fork_data.get(b.name)
        if data is None or data.fork_committed_at is None:
            return (1, 0)
        return (-data.fork_committed_at, -(data.bottom_committed_at or 0))

    return sorted(branches, key=_key)


def persist_fork_points(
    session: Session,
    branches: list[Branch],
    fork_data: dict[str, ForkData],
) -> None:
    """フォークポイントを Branch レコードに書き込む。

    変更がないブランチはスキップする。

    Args:
        session: SQLModel セッション。
        branches: 更新対象のブランチリスト。
        fork_data: ブランチ名 → ForkData のマップ。
    """
    for branch in branches:
        data = fork_data.get(branch.name)
        if data is None:
            continue
        if (branch.fork_hash, branch.fork_committed_at) == (
            data.fork_hash,
            data.fork_committed_at,
        ):
            continue
        branch.fork_hash = data.fork_hash
        branch.fork_committed_at = data.fork_committed_at
        session.add(branch)
    session.commit()
