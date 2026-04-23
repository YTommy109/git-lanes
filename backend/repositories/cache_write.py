"""SQLite キャッシュへの書き込み。"""

from __future__ import annotations

import sqlite3
import time


def insert_repository(conn: sqlite3.Connection, repo_id: str, path: str, name: str) -> None:
    """リポジトリ行を登録する。"""
    conn.execute(
        "INSERT INTO repositories (id, path, name) VALUES (?, ?, ?)",
        (repo_id, path, name),
    )
    conn.commit()


def purge_graph_data(conn: sqlite3.Connection, repo_id: str) -> None:
    """指定リポジトリのグラフ関連行を削除する。"""
    conn.execute(
        "DELETE FROM commit_parents WHERE commit_hash IN "
        "(SELECT hash FROM commits WHERE repo_id = ?)",
        (repo_id,),
    )
    conn.execute("DELETE FROM branches WHERE repo_id = ?", (repo_id,))
    conn.execute("DELETE FROM commits WHERE repo_id = ?", (repo_id,))
    conn.commit()


def update_sync_state(conn: sqlite3.Connection, repo_id: str, head_hex: str | None) -> None:
    """同期メタデータを更新する。"""
    conn.execute(
        "UPDATE repositories SET cached_head = ?, synced_at = ? WHERE id = ?",
        (head_hex, int(time.time()), repo_id),
    )
    conn.commit()


def insert_commit_row(
    conn: sqlite3.Connection,
    repo_id: str,
    full_hash: str,
    short_hash: str,
    message: str,
    author_name: str,
    author_email: str,
    committed_at: int,
) -> None:
    """コミット行を挿入する。"""
    conn.execute(
        "INSERT OR REPLACE INTO commits "
        "(hash, short_hash, message, author_name, author_email, committed_at, repo_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (full_hash, short_hash, message, author_name, author_email, committed_at, repo_id),
    )


def insert_parent_row(
    conn: sqlite3.Connection, commit_hash: str, parent_hash: str, position: int
) -> None:
    """親子関係を挿入する。"""
    conn.execute(
        "INSERT OR REPLACE INTO commit_parents (commit_hash, parent_hash, position) "
        "VALUES (?, ?, ?)",
        (commit_hash, parent_hash, position),
    )


def insert_branch_row(
    conn: sqlite3.Connection, repo_id: str, name: str, tip_hash: str, is_remote: int
) -> None:
    """ブランチ行を挿入する。"""
    conn.execute(
        "INSERT OR REPLACE INTO branches (name, tip_hash, is_remote, repo_id) VALUES (?, ?, ?, ?)",
        (name, tip_hash, is_remote, repo_id),
    )
