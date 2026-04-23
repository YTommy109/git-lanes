"""SQLite キャッシュからの読み取り。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from backend.repositories.ddl import apply_schema


@dataclass(frozen=True)
class RepositoryRecord:
    """登録済みリポジトリの1行。"""

    id: str
    path: str
    name: str
    cached_head: str | None


@dataclass(frozen=True)
class CommitRecord:
    """コミットの1行（表示用）。"""

    hash: str
    short_hash: str
    message: str
    author_name: str
    author_email: str
    committed_at: int


def connect(db_file: str) -> sqlite3.Connection:
    """スキーマ適用済みの接続を返す。

    Args:
        db_file: SQLite ファイルパス。

    Returns:
        接続。
    """
    conn = sqlite3.connect(db_file)
    apply_schema(conn)
    return conn


def get_repository(conn: sqlite3.Connection, repo_id: str) -> RepositoryRecord | None:
    """ID でリポジトリを取得する。"""
    cur = conn.execute(
        "SELECT id, path, name, cached_head FROM repositories WHERE id = ?",
        (repo_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return RepositoryRecord(id=row[0], path=row[1], name=row[2], cached_head=row[3])


def count_commits(conn: sqlite3.Connection, repo_id: str) -> int:
    """コミット件数を返す。"""
    cur = conn.execute("SELECT COUNT(*) FROM commits WHERE repo_id = ?", (repo_id,))
    return int(cur.fetchone()[0])


def list_recent_commits(conn: sqlite3.Connection, repo_id: str, limit: int) -> list[CommitRecord]:
    """新しい順にコミットを返す。"""
    cur = conn.execute(
        "SELECT hash, short_hash, message, author_name, author_email, committed_at "
        "FROM commits WHERE repo_id = ? ORDER BY committed_at DESC LIMIT ?",
        (repo_id, limit),
    )
    return [
        CommitRecord(
            hash=r[0],
            short_hash=r[1],
            message=r[2],
            author_name=r[3],
            author_email=r[4],
            committed_at=r[5],
        )
        for r in cur.fetchall()
    ]


def get_commit(conn: sqlite3.Connection, repo_id: str, commit_hash: str) -> CommitRecord | None:
    """1件のコミットを取得する。"""
    cur = conn.execute(
        "SELECT hash, short_hash, message, author_name, author_email, committed_at "
        "FROM commits WHERE repo_id = ? AND hash = ?",
        (repo_id, commit_hash),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return CommitRecord(
        hash=row[0],
        short_hash=row[1],
        message=row[2],
        author_name=row[3],
        author_email=row[4],
        committed_at=row[5],
    )


def parents_by_child(conn: sqlite3.Connection, child_hashes: list[str]) -> dict[str, list[str]]:
    """複数コミットの親ハッシュをまとめて返す。

    Args:
        conn: SQLite 接続。
        child_hashes: 子コミットのフルハッシュ一覧。

    Returns:
        子ハッシュをキーとし、親は ``position`` 昇順のリスト。
    """
    if not child_hashes:
        return {}
    placeholders = ",".join("?" * len(child_hashes))
    sql = (
        f"SELECT commit_hash, parent_hash FROM commit_parents "
        f"WHERE commit_hash IN ({placeholders}) ORDER BY commit_hash, position"
    )
    cur = conn.execute(sql, child_hashes)
    result: dict[str, list[str]] = {}
    for ch, ph in cur.fetchall():
        result.setdefault(ch, []).append(ph)
    return result
