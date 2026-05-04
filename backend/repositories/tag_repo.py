"""タグ の CRUD 操作。"""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import Tag


def insert_tag_row(session: Session, repo_id: str, name: str, commit_hash: str) -> None:
    """タグ行を挿入または更新する。呼び出し側で commit する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        name: タグ名。
        commit_hash: タグが指すコミットのフルハッシュ。
    """
    session.merge(Tag(name=name, repo_id=repo_id, commit_hash=commit_hash))


def list_tags(session: Session, repo_id: str) -> list[Tag]:
    """リポジトリの全タグを返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        Tag のリスト。
    """
    return list(session.exec(select(Tag).where(Tag.repo_id == repo_id)).all())


def get_tags_for_commit(session: Session, repo_id: str, commit_hash: str) -> list[str]:
    """コミットに付けられたタグ名リストを返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        commit_hash: コミットのフルハッシュ。

    Returns:
        タグ名のリスト。タグなしのときは空リスト。
    """
    rows = session.exec(
        select(Tag).where(Tag.repo_id == repo_id, Tag.commit_hash == commit_hash)
    ).all()
    return [row.name for row in rows]
