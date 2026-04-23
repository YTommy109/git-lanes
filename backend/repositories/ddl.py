"""SQLite のスキーマ定義と適用。"""

import sqlite3

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    cached_head TEXT,
    synced_at INTEGER
);

CREATE TABLE IF NOT EXISTS commits (
    hash TEXT PRIMARY KEY,
    short_hash TEXT NOT NULL,
    message TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_email TEXT NOT NULL,
    committed_at INTEGER NOT NULL,
    repo_id TEXT NOT NULL,
    FOREIGN KEY (repo_id) REFERENCES repositories(id)
);

CREATE INDEX IF NOT EXISTS idx_commits_repo_committed_at
ON commits (repo_id, committed_at DESC);

CREATE TABLE IF NOT EXISTS commit_parents (
    commit_hash TEXT NOT NULL,
    parent_hash TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (commit_hash, parent_hash),
    FOREIGN KEY (commit_hash) REFERENCES commits(hash),
    FOREIGN KEY (parent_hash) REFERENCES commits(hash)
);

CREATE TABLE IF NOT EXISTS branches (
    name TEXT NOT NULL,
    tip_hash TEXT NOT NULL,
    is_remote INTEGER NOT NULL DEFAULT 0,
    repo_id TEXT NOT NULL,
    PRIMARY KEY (name, repo_id),
    FOREIGN KEY (tip_hash) REFERENCES commits(hash),
    FOREIGN KEY (repo_id) REFERENCES repositories(id)
);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    """接続先 DB にテーブル定義を適用する。

    Args:
        conn: SQLite 接続。
    """
    conn.executescript(DDL)
    conn.commit()
