"""SQLModel テーブル定義。"""

from typing import Optional

from sqlalchemy import Column, Index, String
from sqlmodel import Field, SQLModel


class Repository(SQLModel, table=True):
    """Git リポジトリのメタデータ。"""

    __tablename__ = "repositories"

    id: str = Field(primary_key=True)
    path: str = Field(sa_column=Column(String, unique=True, nullable=False))
    name: str = Field(sa_column=Column(String, nullable=False))
    cached_head: Optional[str] = None
    synced_at: Optional[int] = None


class Commit(SQLModel, table=True):
    """コミット情報。"""

    __tablename__ = "commits"

    __table_args__ = (Index("idx_commits_repo_committed_at", "repo_id", "committed_at"),)

    hash: str = Field(primary_key=True)
    short_hash: str = Field(sa_column=Column(String, nullable=False))
    message: str = Field(sa_column=Column(String, nullable=False))
    author_name: str = Field(sa_column=Column(String, nullable=False))
    author_email: str = Field(sa_column=Column(String, nullable=False))
    committed_at: int
    repo_id: str = Field(foreign_key="repositories.id")


class CommitParent(SQLModel, table=True):
    """コミットの親子関係。"""

    __tablename__ = "commit_parents"

    commit_hash: str = Field(primary_key=True, foreign_key="commits.hash")
    parent_hash: str = Field(primary_key=True, foreign_key="commits.hash")
    position: int = Field(default=0)


class Branch(SQLModel, table=True):
    """ブランチ情報。"""

    __tablename__ = "branches"

    name: str = Field(primary_key=True)
    repo_id: str = Field(primary_key=True, foreign_key="repositories.id")
    tip_hash: str = Field(sa_column=Column(String, nullable=False))
    is_remote: int = Field(default=0)
    fork_hash: str | None = Field(default=None)  # フォークポイントのコミットハッシュ
    fork_committed_at: int | None = Field(default=None)  # フォークポイントの UNIX タイムスタンプ


class Tag(SQLModel, table=True):
    """タグ情報。"""

    __tablename__ = "tags"

    name: str = Field(primary_key=True)
    repo_id: str = Field(primary_key=True, foreign_key="repositories.id")
    commit_hash: str = Field(sa_column=Column(String, nullable=False))
