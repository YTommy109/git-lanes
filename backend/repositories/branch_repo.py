"""ブランチ の CRUD 操作。"""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import Branch


def list_branches(session: Session, repo_id: str) -> list[Branch]:
    """リポジトリの全ブランチを返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        Branch のリスト。
    """
    return list(session.exec(select(Branch).where(Branch.repo_id == repo_id)).all())


def insert_branch_row(
    session: Session, repo_id: str, name: str, tip_hash: str, is_remote: int
) -> None:
    """ブランチ行を挿入または更新する。呼び出し側で commit する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        name: ブランチ名。
        tip_hash: ブランチ先端コミットのフルハッシュ。
        is_remote: 0 = ローカル、1 = リモート。
    """
    session.merge(Branch(name=name, repo_id=repo_id, tip_hash=tip_hash, is_remote=is_remote))
