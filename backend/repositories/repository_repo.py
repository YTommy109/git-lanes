"""リポジトリ の CRUD 操作。"""

from __future__ import annotations

import time

from sqlalchemy import delete
from sqlmodel import Session, col, select

from backend.models import Branch, Commit, CommitParent, Repository, Tag


def get_repository(session: Session, repo_id: str) -> Repository | None:
    """ID でリポジトリを取得する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        見つかった場合は Repository、なければ None。
    """
    return session.get(Repository, repo_id)


def list_repositories(session: Session) -> list[Repository]:
    """登録済みリポジトリを name 昇順で全件返す。

    Args:
        session: DB セッション。

    Returns:
        Repository のリスト。0 件のときは空リスト。
    """
    return list(session.exec(select(Repository).order_by(Repository.name)).all())


def get_repository_by_path(session: Session, path: str) -> Repository | None:
    """パスでリポジトリを取得する。

    Args:
        session: DB セッション。
        path: リポジトリの絶対パス。

    Returns:
        見つかった場合は Repository、なければ None。
    """
    return session.exec(select(Repository).where(Repository.path == path)).first()


def insert_repository(session: Session, repo_id: str, path: str, name: str) -> None:
    """リポジトリを登録する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID（UUID）。
        path: リポジトリの絶対パス。
        name: リポジトリ名。

    Raises:
        sqlalchemy.exc.IntegrityError: path が重複している場合。
    """
    session.add(Repository(id=repo_id, path=path, name=name))
    session.commit()


def update_sync_state(session: Session, repo_id: str, head_hex: str | None) -> None:
    """同期済み HEAD ハッシュとタイムスタンプを更新する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        head_hex: 同期済み HEAD のフルハッシュ。None は空リポジトリを示す。
    """
    repo = session.get(Repository, repo_id)
    if repo is None:
        return
    repo.cached_head = head_hex
    repo.synced_at = int(time.time())
    session.add(repo)
    session.commit()


def purge_graph_data(session: Session, repo_id: str) -> None:
    """リポジトリのグラフ関連行を全削除する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
    """
    hashes = [c.hash for c in session.exec(select(Commit).where(Commit.repo_id == repo_id)).all()]
    if hashes:
        # commit_hash と parent_hash の両方を削除する。
        # ワークツリー等で同一ハッシュを共有する場合、parent_hash 側の FK 制約に違反するため。
        session.exec(delete(CommitParent).where(col(CommitParent.commit_hash).in_(hashes)))
        session.exec(delete(CommitParent).where(col(CommitParent.parent_hash).in_(hashes)))
    session.exec(delete(Tag).where(col(Tag.repo_id) == repo_id))
    session.exec(delete(Branch).where(col(Branch.repo_id) == repo_id))
    session.exec(delete(Commit).where(col(Commit.repo_id) == repo_id))
    session.commit()
