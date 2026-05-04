"""コミット・親コミット の CRUD 操作。"""

from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Session, select

from backend.models import Commit, CommitParent


def count_commits(session: Session, repo_id: str) -> int:
    """リポジトリのコミット総数を返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        コミット件数。
    """
    return session.exec(select(func.count(Commit.hash)).where(Commit.repo_id == repo_id)).one()  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]


def list_all_commits(session: Session, repo_id: str) -> list[Commit]:
    """コミットを committed_at 降順で全件返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        コミットのリスト。新しい順に並ぶ。
    """
    return list(
        session.exec(
            select(Commit).where(Commit.repo_id == repo_id).order_by(Commit.committed_at.desc())  # type: ignore[union-attr]  # ty:ignore[unresolved-attribute]
        ).all()
    )


def get_commit(session: Session, repo_id: str, commit_hash: str) -> Commit | None:
    """1件のコミットを取得する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        commit_hash: コミットのフルハッシュ。

    Returns:
        見つかった場合は Commit、なければ None。
    """
    return session.exec(
        select(Commit).where(Commit.repo_id == repo_id, Commit.hash == commit_hash)
    ).first()


def insert_commit_row(
    session: Session,
    repo_id: str,
    full_hash: str,
    short_hash: str,
    message: str,
    author_name: str,
    author_email: str,
    committed_at: int,
) -> None:
    """コミット行を挿入または更新する。呼び出し側で commit する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        full_hash: コミットのフルハッシュ。
        short_hash: 短縮ハッシュ（7文字）。
        message: コミットメッセージ1行目。
        author_name: 作者名。
        author_email: 作者メールアドレス。
        committed_at: UNIX タイムスタンプ。
    """
    session.merge(
        Commit(
            hash=full_hash,
            short_hash=short_hash,
            message=message,
            author_name=author_name,
            author_email=author_email,
            committed_at=committed_at,
            repo_id=repo_id,
        )
    )


def parents_by_child(session: Session, child_hashes: list[str]) -> dict[str, list[str]]:
    """複数コミットの親ハッシュをまとめて返す。

    Args:
        session: DB セッション。
        child_hashes: 子コミットのフルハッシュ一覧。

    Returns:
        子ハッシュをキーとし、親を position 昇順で格納した辞書。
    """
    if not child_hashes:
        return {}
    rows = session.exec(
        select(CommitParent)
        .where(CommitParent.commit_hash.in_(child_hashes))  # type: ignore[union-attr]  # ty:ignore[unresolved-attribute]
        .order_by(CommitParent.commit_hash, CommitParent.position)  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    ).all()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row.commit_hash, []).append(row.parent_hash)
    return result


def insert_parent_row(session: Session, commit_hash: str, parent_hash: str, position: int) -> None:
    """親子関係行を挿入または更新する。呼び出し側で commit する。

    Args:
        session: DB セッション。
        commit_hash: 子コミットのフルハッシュ。
        parent_hash: 親コミットのフルハッシュ。
        position: 親の順序（0: 第1親）。
    """
    session.merge(CommitParent(commit_hash=commit_hash, parent_hash=parent_hash, position=position))
