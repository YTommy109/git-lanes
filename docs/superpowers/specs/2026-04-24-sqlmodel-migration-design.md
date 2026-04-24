# SQLModel 全面移行設計書

**作成日**: 2026-04-24
**対象ブランチ**: feature/first_step

---

## 概要

現在 `sqlite3` 標準ライブラリで直接記述している DB 操作を、SQLModel に全面置き換えする。
FastAPI の `Depends` パターンを採用し、セッション管理をフレームワークに委ねることで、
テスト容易性と型安全性を高める。

---

## 背景と目的

### 現状の課題

- `sqlite3` + 手書き SQL 文字列でテーブル定義・CRUD を管理している
- `ddl.py`（DDL 文字列）・`cache_read.py`・`cache_write.py` の3ファイルで責務が分散している
- `contextlib.closing()` による接続管理がルーター/サービス層に散在している
- テスト用の DB パス切り替えを環境変数で行っており、テスト間の分離が不完全

### 移行後の利点

- SQLModel モデルがテーブル定義・バリデーション・型ヒントを一元化する
- FastAPI の `Depends(get_session)` でセッションライフサイクルをフレームワークに委ねられる
- インメモリ SQLite によるテストフィクスチャで、テストを完全に分離できる
- DDL 管理（`IF NOT EXISTS` など）が `SQLModel.metadata.create_all()` に統合される

---

## アーキテクチャ変更

### ファイル構成

**削除するファイル**

```
backend/repositories/ddl.py        # DDL 文字列 → SQLModel モデルに統合
backend/repositories/cache_read.py # sqlite3 SELECT → cache_repo.py に統合
backend/repositories/cache_write.py # sqlite3 CRUD → cache_repo.py に統合
```

**新規作成するファイル**

```
backend/models.py                  # SQLModel テーブル定義（4クラス）
backend/db.py                      # エンジン・get_session・テーブル初期化
backend/repositories/cache_repo.py # 読み書き統合した CRUD 関数群
```

**変更するファイル**

```
backend/main.py           # startup で create_db_and_tables() を呼ぶ
backend/services/sync_service.py  # conn → session に変更
backend/routers/html.py   # Depends(get_session) を使用
backend/routers/api.py    # Depends(get_session) を使用
```

**変更しないファイル**

```
backend/repositories/git_repo.py  # pygit2 操作は SQLModel と無関係
backend/paths.py                  # DB パス解決ロジックをそのまま流用
```

---

## モデル定義（backend/models.py）

テーブル名は現行の複数形（`commits`, `branches` 等）を維持する。
Relationship フィールドは使用しない（クエリはすべて明示的 `select()` で記述）。

```python
from typing import Optional
from sqlmodel import SQLModel, Field

class Repository(SQLModel, table=True):
    __tablename__ = "repositories"
    id: str = Field(primary_key=True)
    path: str = Field(unique=True)
    name: str
    cached_head: Optional[str] = None
    synced_at: Optional[int] = None

class Commit(SQLModel, table=True):
    __tablename__ = "commits"
    hash: str = Field(primary_key=True)
    short_hash: str
    message: str
    author_name: str
    author_email: str
    committed_at: int
    repo_id: str = Field(foreign_key="repositories.id")

class CommitParent(SQLModel, table=True):
    __tablename__ = "commit_parents"
    commit_hash: str = Field(primary_key=True, foreign_key="commits.hash")
    parent_hash: str = Field(primary_key=True, foreign_key="commits.hash")
    position: int = Field(default=0)

class Branch(SQLModel, table=True):
    __tablename__ = "branches"
    name: str = Field(primary_key=True)
    repo_id: str = Field(primary_key=True, foreign_key="repositories.id")
    tip_hash: str = Field(foreign_key="commits.hash")
    is_remote: int = Field(default=0)
```

**設計判断**

- `is_remote` は `bool` ではなく `int` で維持（SQLite に bool 型がないため）
- `CommitParent` と `Branch` は複合主キー（2フィールドに `primary_key=True`）
- `RepositoryRecord` / `CommitRecord` データクラスは廃止。SQLModel モデルが Pydantic モデルを兼ねるため、上位層にそのまま渡せる

---

## エンジン・セッション管理（backend/db.py）

```python
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from backend.paths import primary_db_path

engine = create_engine(
    f"sqlite:///{primary_db_path()}",
    connect_args={"check_same_thread": False},
)

def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
```

**設計判断**

- `check_same_thread=False` は SQLite + FastAPI（非同期）の組み合わせで必須
- `primary_db_path()` をそのまま流用するため `GIT_LANES_DATA_DIR` 環境変数によるパス切り替えも継続して動作する
- `engine` はモジュールレベルのシングルトン（1プロセス1インスタンス）

---

## リポジトリ層（backend/repositories/cache_repo.py）

### 関数シグネチャ対応表

| 旧関数（cache_read / cache_write） | 新関数（cache_repo） | 実装方法 |
| --- | --- | --- |
| `get_repository(conn, repo_id)` | `get_repository(session, repo_id)` | `session.get(Repository, repo_id)` |
| `count_commits(conn, repo_id)` | `count_commits(session, repo_id)` | `select(func.count()).where(...)` |
| `list_recent_commits(conn, repo_id, limit)` | 同左 | `select(Commit).order_by(...).limit(...)` |
| `get_commit(conn, repo_id, hash)` | `get_commit(session, repo_id, hash)` | `select(Commit).where(...)` |
| `parents_by_child(conn, hashes)` | `parents_by_child(session, hashes)` | `.in_()` + `.order_by(position)` |
| `insert_repository(conn, ...)` | `insert_repository(session, ...)` | `session.add()` + `session.commit()` |
| `purge_graph_data(conn, repo_id)` | `purge_graph_data(session, repo_id)` | `delete()` × 3テーブル（FK 順序維持） |
| `update_sync_state(conn, ...)` | `update_sync_state(session, ...)` | フィールド代入 + `session.commit()` |
| `insert_commit_row(conn, ...)` | `insert_commit_row(session, ...)` | `session.merge(Commit(...))` |
| `insert_parent_row(conn, ...)` | `insert_parent_row(session, ...)` | `session.merge(CommitParent(...))` |
| `insert_branch_row(conn, ...)` | `insert_branch_row(session, ...)` | `session.merge(Branch(...))` |

### トランザクション管理方針

- `insert_repository` / `purge_graph_data` / `update_sync_state` は関数内で `session.commit()` する
- `insert_commit_row` / `insert_parent_row` / `insert_branch_row` は `session.commit()` しない
  - 呼び出し側（`sync_service`）がバルク挿入後に一括 `session.commit()` する設計を維持する

### INSERT OR REPLACE の扱い

`session.merge(Model(...))` を使用する。主キーが存在すれば UPDATE、なければ INSERT を SQLAlchemy が自動判定する。

---

## サービス・ルーター層の変更

### sync_service.py

```python
# 変更前
def sync_repo(repo_id: str, conn: sqlite3.Connection) -> None: ...

# 変更後
def sync_repo(repo_id: str, session: Session) -> None: ...
```

### routers/html.py / api.py

```python
# 変更前
from contextlib import closing
from backend.repositories import cache_read

@router.get("/repos/{repo_id}/graph")
async def graph(repo_id: str, request: Request):
    with closing(cache_read.connect(...)) as conn:
        repo = cache_read.get_repository(conn, repo_id)

# 変更後
from sqlmodel import Session
from fastapi import Depends
from backend.db import get_session
from backend.repositories import cache_repo

@router.get("/repos/{repo_id}/graph")
async def graph(repo_id: str, request: Request, session: Session = Depends(get_session)):
    repo = cache_repo.get_repository(session, repo_id)
```

---

## テスト戦略

### フィクスチャ（インメモリ DB）

```python
# tests/unit/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

既存の統合テスト（`GIT_LANES_DATA_DIR` 方式）はそのまま維持する。

### 単体テストケース一覧

| 対象関数 | テストケース |
| --- | --- |
| `get_repository` | 存在するID / 存在しないID（None を返す） |
| `count_commits` | 0件 / N件 |
| `list_recent_commits` | limit 以下 / limit 超え / committed_at 降順 |
| `get_commit` | 存在する / 存在しない |
| `parents_by_child` | 空リスト / 単親 / マージコミット（複数親・position 順） |
| `insert_repository` | 正常挿入 / path 重複でエラー |
| `purge_graph_data` | commit_parents → branches → commits の順で削除 |
| `update_sync_state` | cached_head と synced_at が更新される |
| `insert_commit_row` | 新規挿入 / 重複時に REPLACE（フィールド更新） |
| `insert_branch_row` | 新規挿入 / tip_hash 更新 |

---

## 実装順序

依存関係の少ない順に実装する。

1. `backend/models.py`（新規・依存なし）
2. `backend/db.py`（新規・models に依存）
3. `backend/repositories/cache_repo.py`（新規・models + db に依存）
4. `tests/unit/test_cache_repo.py`（新規・cache_repo に依存）
5. `backend/services/sync_service.py`（修正・cache_repo に依存）
6. `backend/routers/html.py` / `api.py`（修正・db + cache_repo に依存）
7. `backend/main.py`（修正・db に依存）
8. 旧ファイル削除（`ddl.py` / `cache_read.py` / `cache_write.py`）
