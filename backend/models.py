"""SQLModel テーブル定義。"""

from typing import Optional

from sqlmodel import Field, SQLModel


class Repository(SQLModel, table=True):
    """Git リポジトリのメタデータ。"""

    __tablename__ = "repositories"

    id: str = Field(primary_key=True)
    path: str = Field(unique=True)
    name: str
    cached_head: Optional[str] = None
    synced_at: Optional[int] = None


class Commit(SQLModel, table=True):
    """コミット情報。"""

    __tablename__ = "commits"

    hash: str = Field(primary_key=True)
    short_hash: str
    message: str
    author_name: str
    author_email: str
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
    tip_hash: str = Field(foreign_key="commits.hash")
    is_remote: int = Field(default=0)
