# SQLModel 全面移行 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sqlite3` 直接操作を SQLModel + FastAPI Depends パターンに全面置き換えする

**Architecture:** `backend/models.py` に SQLModel テーブル定義、`backend/db.py` にエンジン・セッション管理を集約し、`cache_repo.py` が Session を受け取る CRUD 関数を提供する。ルーターは `Depends(get_session)` でセッションを受け取り、`contextlib.closing()` を廃止する。

**Tech Stack:** SQLModel 0.0.21+、SQLAlchemy（SQLModel に同梱）、FastAPI Depends、pytest（インメモリ DB フィクスチャ）

---

## ファイル構成

| 操作 | パス | 役割 |
| --- | --- | --- |
| 新規 | `backend/models.py` | SQLModel テーブル定義（4クラス） |
| 新規 | `backend/db.py` | エンジン・get_session・テーブル初期化 |
| 新規 | `backend/repositories/cache_repo.py` | 読み書き統合 CRUD（11関数） |
| 新規 | `tests/unit/conftest.py` | session フィクスチャ（インメモリ DB） |
| 新規 | `tests/unit/test_cache_repo.py` | cache_repo の単体テスト |
| 修正 | `backend/services/sync_service.py` | conn → session に変更 |
| 修正 | `tests/unit/test_sync_service.py` | session フィクスチャを使うよう書き換え |
| 修正 | `backend/routers/html.py` | Depends(get_session) を使用 |
| 修正 | `backend/routers/api.py` | Depends(get_session)・IntegrityError 差し替え |
| 修正 | `backend/main.py` | lifespan で create_db_and_tables() 呼び出し |
| 削除 | `backend/repositories/ddl.py` | SQLModel に統合 |
| 削除 | `backend/repositories/cache_read.py` | cache_repo に統合 |
| 削除 | `backend/repositories/cache_write.py` | cache_repo に統合 |

---

## Task 1: backend/models.py を作成する

**Files:**
- Create: `backend/models.py`

- [ ] **Step 1: ファイルを作成する**

```python
# backend/models.py
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
```

- [ ] **Step 2: インポートが通ることを確認する**

```bash
cd /path/to/repo
uv run python -c "from backend.models import Repository, Commit, CommitParent, Branch; print('OK')"
```

期待出力: `OK`

- [ ] **Step 3: コミットする**

```bash
git add backend/models.py
git commit -m "feat: SQLModel テーブル定義を追加する"
```

---

## Task 2: backend/db.py を作成する

**Files:**
- Create: `backend/db.py`

- [ ] **Step 1: ファイルを作成する**

```python
# backend/db.py
"""エンジン・セッション管理。"""

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from backend.paths import primary_db_path

engine = create_engine(
    f"sqlite:///{primary_db_path()}",
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    """テーブルが未存在の場合のみ作成する。"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI の Depends 用セッションジェネレータ。"""
    with Session(engine) as session:
        yield session
```

- [ ] **Step 2: インポートが通ることを確認する**

```bash
uv run python -c "from backend.db import create_db_and_tables, get_session; print('OK')"
```

期待出力: `OK`

- [ ] **Step 3: コミットする**

```bash
git add backend/db.py
git commit -m "feat: SQLModel エンジン・セッション管理を追加する"
```

---

## Task 3: テストフィクスチャと cache_repo の失敗テストを書く

**Files:**
- Create: `tests/unit/conftest.py`
- Create: `tests/unit/test_cache_repo.py`

- [ ] **Step 1: tests/unit/conftest.py を作成する**

```python
# tests/unit/conftest.py
"""単体テスト共通フィクスチャ。"""

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

import backend.models  # noqa: F401 — テーブル登録のため必要


@pytest.fixture(name="session")
def session_fixture():
    """インメモリ SQLite セッションを返す。"""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

- [ ] **Step 2: tests/unit/test_cache_repo.py を作成する（失敗テスト）**

```python
# tests/unit/test_cache_repo.py
"""cache_repo の単体テスト。"""

import time

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backend.models import Branch, Commit, CommitParent, Repository
from backend.repositories import cache_repo


# ── ヘルパー ──────────────────────────────────────────────


def _add_repo(session: Session, repo_id: str = "r1") -> Repository:
    """テスト用リポジトリを登録して返す。"""
    cache_repo.insert_repository(session, repo_id, f"/path/{repo_id}", repo_id)
    return cache_repo.get_repository(session, repo_id)


def _add_commit(
    session: Session,
    repo_id: str,
    hash: str,
    committed_at: int = 1000,
) -> Commit:
    """テスト用コミットを挿入して返す。"""
    cache_repo.insert_commit_row(
        session, repo_id, hash, hash[:7], "msg", "author", "a@b.com", committed_at
    )
    return cache_repo.get_commit(session, repo_id, hash)


# ── get_repository ─────────────────────────────────────────


def test_get_repository_存在するIDを返す(session):
    # --- Arrange ---
    cache_repo.insert_repository(session, "r1", "/path/r1", "r1")

    # --- Act ---
    result = cache_repo.get_repository(session, "r1")

    # --- Assert ---
    assert result is not None
    assert result.id == "r1"
    assert result.path == "/path/r1"


def test_get_repository_存在しないIDはNoneを返す(session):
    # --- Act ---
    result = cache_repo.get_repository(session, "no-such-id")

    # --- Assert ---
    assert result is None


# ── count_commits ──────────────────────────────────────────


def test_count_commits_0件(session):
    # --- Arrange ---
    _add_repo(session)

    # --- Act & Assert ---
    assert cache_repo.count_commits(session, "r1") == 0


def test_count_commits_N件(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)

    # --- Act & Assert ---
    assert cache_repo.count_commits(session, "r1") == 2


# ── list_recent_commits ────────────────────────────────────


def test_list_recent_commits_committed_at降順(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40, committed_at=100)
    _add_commit(session, "r1", "b" * 40, committed_at=200)

    # --- Act ---
    rows = cache_repo.list_recent_commits(session, "r1", 10)

    # --- Assert ---
    assert [r.committed_at for r in rows] == [200, 100]


def test_list_recent_commits_limit超えは切り捨て(session):
    # --- Arrange ---
    _add_repo(session)
    for i in range(5):
        _add_commit(session, "r1", str(i) * 40, committed_at=i)

    # --- Act ---
    rows = cache_repo.list_recent_commits(session, "r1", 3)

    # --- Assert ---
    assert len(rows) == 3


# ── get_commit ─────────────────────────────────────────────


def test_get_commit_存在するコミットを返す(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)

    # --- Act ---
    result = cache_repo.get_commit(session, "r1", "a" * 40)

    # --- Assert ---
    assert result is not None
    assert result.hash == "a" * 40


def test_get_commit_存在しないはNoneを返す(session):
    # --- Arrange ---
    _add_repo(session)

    # --- Act ---
    result = cache_repo.get_commit(session, "r1", "z" * 40)

    # --- Assert ---
    assert result is None


# ── parents_by_child ───────────────────────────────────────


def test_parents_by_child_空リストは空dictを返す(session):
    # --- Act ---
    result = cache_repo.parents_by_child(session, [])

    # --- Assert ---
    assert result == {}


def test_parents_by_child_単親コミット(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)
    cache_repo.insert_parent_row(session, "b" * 40, "a" * 40, 0)
    session.commit()

    # --- Act ---
    result = cache_repo.parents_by_child(session, ["b" * 40])

    # --- Assert ---
    assert result == {"b" * 40: ["a" * 40]}


def test_parents_by_child_マージコミットはposition順(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)
    _add_commit(session, "r1", "c" * 40)
    cache_repo.insert_parent_row(session, "c" * 40, "a" * 40, 0)
    cache_repo.insert_parent_row(session, "c" * 40, "b" * 40, 1)
    session.commit()

    # --- Act ---
    result = cache_repo.parents_by_child(session, ["c" * 40])

    # --- Assert ---
    assert result == {"c" * 40: ["a" * 40, "b" * 40]}


# ── insert_repository ──────────────────────────────────────


def test_insert_repository_正常挿入(session):
    # --- Act ---
    cache_repo.insert_repository(session, "r1", "/path/r1", "repo1")

    # --- Assert ---
    rec = cache_repo.get_repository(session, "r1")
    assert rec is not None
    assert rec.name == "repo1"


def test_insert_repository_パス重複はIntegrityError(session):
    # --- Arrange ---
    cache_repo.insert_repository(session, "r1", "/path/same", "repo1")

    # --- Act & Assert ---
    with pytest.raises(IntegrityError):
        cache_repo.insert_repository(session, "r2", "/path/same", "repo2")


# ── purge_graph_data ───────────────────────────────────────


def test_purge_graph_data_commit_parents_branches_commitsが削除される(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)
    cache_repo.insert_parent_row(session, "b" * 40, "a" * 40, 0)
    cache_repo.insert_branch_row(session, "r1", "main", "b" * 40, 0)
    session.commit()

    # --- Act ---
    cache_repo.purge_graph_data(session, "r1")

    # --- Assert ---
    assert cache_repo.count_commits(session, "r1") == 0
    assert cache_repo.parents_by_child(session, ["b" * 40]) == {}


# ── update_sync_state ──────────────────────────────────────


def test_update_sync_state_cached_headとsynced_atが更新される(session):
    # --- Arrange ---
    _add_repo(session)
    before = int(time.time())

    # --- Act ---
    cache_repo.update_sync_state(session, "r1", "abc123")

    # --- Assert ---
    rec = cache_repo.get_repository(session, "r1")
    assert rec is not None
    assert rec.cached_head == "abc123"
    assert rec.synced_at is not None
    assert rec.synced_at >= before


# ── insert_commit_row（REPLACE） ───────────────────────────


def test_insert_commit_row_重複時はフィールドが更新される(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)

    # --- Act ---
    cache_repo.insert_commit_row(
        session, "r1", "a" * 40, "aaaaaaa", "updated msg", "new", "n@b.com", 9999
    )
    session.commit()

    # --- Assert ---
    rec = cache_repo.get_commit(session, "r1", "a" * 40)
    assert rec is not None
    assert rec.message == "updated msg"


# ── insert_branch_row（REPLACE） ───────────────────────────


def test_insert_branch_row_tip_hashが更新される(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    _add_commit(session, "r1", "b" * 40)
    cache_repo.insert_branch_row(session, "r1", "main", "a" * 40, 0)
    session.commit()

    # --- Act ---
    cache_repo.insert_branch_row(session, "r1", "main", "b" * 40, 0)
    session.commit()

    # --- Assert ---
    from sqlmodel import select
    from backend.models import Branch
    branch = session.exec(
        select(Branch).where(Branch.name == "main", Branch.repo_id == "r1")
    ).first()
    assert branch is not None
    assert branch.tip_hash == "b" * 40
```

- [ ] **Step 3: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_cache_repo.py -v 2>&1 | head -20
```

期待出力: `ImportError: cannot import name 'cache_repo'` または同等のエラー

- [ ] **Step 4: コミットする**

```bash
git add tests/unit/conftest.py tests/unit/test_cache_repo.py
git commit -m "test: cache_repo の失敗テストを追加する"
```

---

## Task 4: backend/repositories/cache_repo.py を実装する

**Files:**
- Create: `backend/repositories/cache_repo.py`
- Test: `tests/unit/test_cache_repo.py`

- [ ] **Step 1: ファイルを作成する**

```python
# backend/repositories/cache_repo.py
"""SQLModel ベースの CRUD 操作。"""

from __future__ import annotations

import time

from sqlalchemy import delete, func
from sqlmodel import Session, select

from backend.models import Branch, Commit, CommitParent, Repository


def get_repository(session: Session, repo_id: str) -> Repository | None:
    """ID でリポジトリを取得する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        見つかった場合は Repository、なければ None。
    """
    return session.get(Repository, repo_id)


def count_commits(session: Session, repo_id: str) -> int:
    """リポジトリのコミット総数を返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        コミット件数。
    """
    return session.exec(
        select(func.count(Commit.hash)).where(Commit.repo_id == repo_id)
    ).one()


def list_recent_commits(session: Session, repo_id: str, limit: int) -> list[Commit]:
    """committed_at 降順で最新コミットを返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        limit: 取得上限数。

    Returns:
        コミットのリスト。新しい順に並ぶ。
    """
    return list(
        session.exec(
            select(Commit)
            .where(Commit.repo_id == repo_id)
            .order_by(Commit.committed_at.desc())
            .limit(limit)
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
        .where(CommitParent.commit_hash.in_(child_hashes))
        .order_by(CommitParent.commit_hash, CommitParent.position)
    ).all()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row.commit_hash, []).append(row.parent_hash)
    return result


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


def purge_graph_data(session: Session, repo_id: str) -> None:
    """リポジトリのグラフ関連行を全削除する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
    """
    hashes = [
        c.hash
        for c in session.exec(select(Commit).where(Commit.repo_id == repo_id)).all()
    ]
    if hashes:
        session.exec(delete(CommitParent).where(CommitParent.commit_hash.in_(hashes)))
    session.exec(delete(Branch).where(Branch.repo_id == repo_id))
    session.exec(delete(Commit).where(Commit.repo_id == repo_id))
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


def insert_parent_row(
    session: Session, commit_hash: str, parent_hash: str, position: int
) -> None:
    """親子関係行を挿入または更新する。呼び出し側で commit する。

    Args:
        session: DB セッション。
        commit_hash: 子コミットのフルハッシュ。
        parent_hash: 親コミットのフルハッシュ。
        position: 親の順序（0: 第1親）。
    """
    session.merge(
        CommitParent(commit_hash=commit_hash, parent_hash=parent_hash, position=position)
    )


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
```

- [ ] **Step 2: テストを実行してすべて通ることを確認する**

```bash
uv run pytest tests/unit/test_cache_repo.py -v
```

期待出力: 全テスト PASSED

- [ ] **Step 3: コミットする**

```bash
git add backend/repositories/cache_repo.py
git commit -m "feat: SQLModel ベースの cache_repo を実装する"
```

---

## Task 5: sync_service と test_sync_service を更新する

**Files:**
- Modify: `backend/services/sync_service.py`
- Modify: `tests/unit/test_sync_service.py`

- [ ] **Step 1: sync_service.py を書き換える**

```python
# backend/services/sync_service.py
"""Git リポジトリから SQLite キャッシュへ同期する。"""

from __future__ import annotations

import pygit2
from sqlmodel import Session

from backend.repositories import cache_repo
from backend.repositories.git_repo import (
    iter_local_branches,
    open_repository,
    walk_commits_from_head,
)


def _head_hex_or_none(repo: pygit2.Repository) -> str | None:
    try:
        return str(repo.head.target)
    except (KeyError, pygit2.GitError):
        return None


def _should_resync(session: Session, repo_id: str, head_hex: str | None) -> bool:
    if cache_repo.get_repository(session, repo_id) is None:
        return False
    if head_hex is None:
        return True
    if cache_repo.count_commits(session, repo_id) == 0:
        return True
    rec = cache_repo.get_repository(session, repo_id)
    assert rec is not None
    return rec.cached_head != head_hex


def sync_repository(session: Session, repo_id: str, repo_path: str) -> None:
    """必要ならリポジトリ内容をフル再同期する。

    HEAD が前回同期時と同じでコミットが残っていれば何もしない。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo_path: Git 作業コピーのパス。
    """
    repo = open_repository(repo_path)
    head_hex = _head_hex_or_none(repo)
    if not _should_resync(session, repo_id, head_hex):
        return
    cache_repo.purge_graph_data(session, repo_id)
    if head_hex is None:
        cache_repo.update_sync_state(session, repo_id, None)
        return
    _sync_commits_and_branches(session, repo_id, repo, head_hex)


def _sync_commits_and_branches(
    session: Session,
    repo_id: str,
    repo: pygit2.Repository,
    head_hex: str,
) -> None:
    """コミット・ブランチをキャッシュに書き込む。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo: pygit2 リポジトリ。
        head_hex: 現在の HEAD ハッシュ。
    """
    commits = walk_commits_from_head(repo)
    # 親ハッシュへの外部キー制約を満たすため、コミットを先に全件挿入する。
    for c in commits:
        message_line = c.message.split("\n", 1)[0]
        cid = str(c.id)
        cache_repo.insert_commit_row(
            session, repo_id, cid, cid[:7], message_line,
            c.author.name, c.author.email, int(c.commit_time),
        )
    for c in commits:
        for pos, parent_id in enumerate(c.parent_ids):
            cache_repo.insert_parent_row(session, str(c.id), str(parent_id), pos)
    try:
        for branch_name, tip in iter_local_branches(repo):
            cache_repo.insert_branch_row(session, repo_id, branch_name, tip, 0)
    except pygit2.GitError:
        pass
    session.commit()
    cache_repo.update_sync_state(session, repo_id, head_hex)
```

- [ ] **Step 2: test_sync_service.py を書き換える**

```python
# tests/unit/test_sync_service.py
"""sync_service の単体テスト。"""

import uuid

import pygit2

from backend.repositories import cache_repo
from backend.services import sync_service
from tests.support.git_repo_fixture import make_two_commit_repo


def test_sync_repository_writes_commits(session, tmp_path):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    assert cache_repo.count_commits(session, repo_id) == 2
    rec = cache_repo.get_repository(session, repo_id)
    assert rec is not None
    assert rec.cached_head is not None


def test_sync_repository_handles_empty_repo(session, tmp_path):
    # --- Arrange ---
    repo_path = tmp_path / "empty"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "empty")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    assert cache_repo.count_commits(session, repo_id) == 0
```

- [ ] **Step 3: テストを実行して通ることを確認する**

```bash
uv run pytest tests/unit/test_sync_service.py tests/unit/test_cache_repo.py -v
```

期待出力: 全テスト PASSED

- [ ] **Step 4: コミットする**

```bash
git add backend/services/sync_service.py tests/unit/test_sync_service.py
git commit -m "refactor: sync_service を Session ベースに移行する"
```

---

## Task 6: backend/routers/html.py を更新する

**Files:**
- Modify: `backend/routers/html.py`

- [ ] **Step 1: html.py を書き換える**

```python
# backend/routers/html.py
"""HTML 応答（htmx 向け）。"""

from __future__ import annotations

from pathlib import Path

import pygit2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from backend.db import get_session
from backend.repositories import cache_repo
from backend.services import graph_layout, sync_service
from backend.validation import parse_commit_hash, parse_repo_id

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["html"])


@router.get("/", response_class=HTMLResponse)
async def welcome(request: Request) -> HTMLResponse:
    """ウェルカム画面を返す。"""
    return templates.TemplateResponse(request, "welcome.html", {})


@router.get("/repos/{repo_id}/graph", response_class=HTMLResponse)
async def graph_page(
    request: Request,
    repo_id: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ブランチグラフ画面を返す。"""
    rid = parse_repo_id(repo_id)
    rec = cache_repo.get_repository(session, rid)
    if rec is None:
        raise HTTPException(status_code=404, detail="リポジトリが見つかりません")
    try:
        sync_service.sync_repository(session, rid, rec.path)
    except pygit2.GitError as exc:
        raise HTTPException(status_code=400, detail="Git リポジトリを開けません") from exc
    rows = cache_repo.list_recent_commits(session, rid, 50)
    parents = cache_repo.parents_by_child(session, [r.hash for r in rows])
    nodes, edges = graph_layout.build_single_lane_layout(rows, parents)
    position_by_hash = {n.commit.hash: n for n in nodes}
    row_spacing = 52.0
    svg_height = 80.0 + max(len(nodes), 1) * row_spacing
    return templates.TemplateResponse(
        request,
        "graph.html",
        {
            "repo_id": rid,
            "repo_name": rec.name,
            "nodes": nodes,
            "edges": edges,
            "position_by_hash": position_by_hash,
            "svg_height": svg_height,
        },
    )


@router.get(
    "/repos/{repo_id}/commits/{commit_hash}/detail",
    response_class=HTMLResponse,
)
async def commit_detail(
    request: Request,
    repo_id: str,
    commit_hash: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """コミット詳細の HTML 断片を返す（htmx 用）。"""
    rid = parse_repo_id(repo_id)
    ch = parse_commit_hash(commit_hash)
    row = cache_repo.get_commit(session, rid, ch)
    if row is None:
        raise HTTPException(status_code=404, detail="コミットが見つかりません")
    return templates.TemplateResponse(request, "partials/detail.html", {"commit": row})
```

- [ ] **Step 2: lint を確認する**

```bash
uv run ruff check backend/routers/html.py
```

期待出力: エラーなし

- [ ] **Step 3: コミットする**

```bash
git add backend/routers/html.py
git commit -m "refactor: html ルーターを Depends(get_session) に移行する"
```

---

## Task 7: backend/routers/api.py を更新する

**Files:**
- Modify: `backend/routers/api.py`

- [ ] **Step 1: api.py を書き換える**

`sqlite3.IntegrityError` を `sqlalchemy.exc.IntegrityError` に差し替える点に注意。

```python
# backend/routers/api.py
"""登録などの HTTP API。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

import pygit2
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backend.db import get_session
from backend.repositories import cache_repo
from backend.repositories.git_repo import open_repository

router = APIRouter(tags=["api"])


@router.post("/api/repos")
async def register_repository(
    path: Annotated[str, Form()],
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """フォルダパスからリポジトリを登録し、グラフ画面へリダイレクトする。"""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="ディレクトリが存在しません")
    try:
        open_repository(str(resolved))
    except pygit2.GitError as exc:
        raise HTTPException(status_code=400, detail="Git リポジトリとして開けません") from exc
    repo_id = str(uuid.uuid4())
    try:
        cache_repo.insert_repository(session, repo_id, str(resolved), resolved.name)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="このパスは既に登録されています") from exc
    return RedirectResponse(url=f"/repos/{repo_id}/graph", status_code=303)
```

- [ ] **Step 2: lint を確認する**

```bash
uv run ruff check backend/routers/api.py
```

期待出力: エラーなし

- [ ] **Step 3: コミットする**

```bash
git add backend/routers/api.py
git commit -m "refactor: api ルーターを Depends(get_session) に移行する"
```

---

## Task 8: backend/main.py を更新する

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: main.py を書き換える**

```python
# backend/main.py
"""FastAPI アプリケーションのエントリポイント。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.db import create_db_and_tables
from backend.routers import api, html

ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時にテーブルを作成する。"""
    create_db_and_tables()
    yield


app = FastAPI(title="Git Lanes", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.include_router(html.router)
app.include_router(api.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """サーバーの稼働確認用エンドポイント。"""
    return {"status": "ok"}
```

- [ ] **Step 2: ヘルスチェックテストが通ることを確認する**

```bash
uv run pytest tests/unit/test_app.py -v
```

期待出力: PASSED

- [ ] **Step 3: コミットする**

```bash
git add backend/main.py
git commit -m "refactor: main.py に lifespan を追加してテーブル初期化を行う"
```

---

## Task 9: 旧ファイルを削除して全テストを確認する

**Files:**
- Delete: `backend/repositories/ddl.py`
- Delete: `backend/repositories/cache_read.py`
- Delete: `backend/repositories/cache_write.py`

- [ ] **Step 1: 旧ファイルを削除する**

```bash
git rm backend/repositories/ddl.py \
       backend/repositories/cache_read.py \
       backend/repositories/cache_write.py
```

- [ ] **Step 2: 全テストを実行して通ることを確認する**

```bash
uv run pytest -v
```

期待出力: 全テスト PASSED、カバレッジ 85% 以上

- [ ] **Step 3: lint・format を確認する**

```bash
uv run ruff check .
uv run ruff format --check .
```

期待出力: エラーなし

- [ ] **Step 4: コミットする**

```bash
git commit -m "refactor: sqlite3 直接操作の旧ファイルを削除する"
```
