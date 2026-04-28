# watchdog 自動同期 & SSE リアルタイム更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** watchdog で `.git/HEAD` / `.git/refs/` の変化を検知し、SQLite キャッシュ更新後に SSE でブラウザへ通知してグラフ画面を自動リロードする。

**Architecture:** watchdog スレッドが GitEventHandler 経由で `sync_repository()` を呼び出し、完了後に `EventBus.notify()` で asyncio ループへ通知する。FastAPI の SSE エンドポイントがブラウザへイベントをプッシュし、htmx SSE 拡張 + hyperscript がページリロードをトリガーする。

**Tech Stack:** watchdog 6.x（既存依存）、sse-starlette 2.x（新規追加）、htmx SSE 拡張（CDN）、hyperscript（既存）

---

## ファイル構成

| ファイル | 種別 | 責務 |
|----------|------|------|
| `backend/services/event_bus.py` | 新規 | repo_id ごとの asyncio.Queue 管理・スレッドセーフ通知 |
| `backend/services/watch_service.py` | 新規 | watchdog Observer 管理・GitEventHandler・デバウンス |
| `backend/routers/graph_events.py` | 新規 | `GET /repos/{repo_id}/events` SSE エンドポイント |
| `backend/main.py` | 変更 | lifespan で Observer 起動・停止・既存リポジトリの監視開始 |
| `backend/routers/api.py` | 変更 | リポジトリ登録時に `WatchService.watch()` を呼ぶ |
| `backend/templates/base.html` | 変更 | htmx SSE 拡張スクリプトを追加 |
| `backend/templates/graph.html` | 変更 | SSE 接続タグと hyperscript リロードを追加 |
| `pyproject.toml` | 変更 | `sse-starlette>=2.1` 依存追加 |
| `tests/unit/test_event_bus.py` | 新規 | EventBus の単体テスト |
| `tests/unit/test_watch_service.py` | 新規 | WatchService / GitEventHandler の単体テスト |
| `tests/unit/test_graph_events.py` | 新規 | SSE エンドポイントの単体テスト |

---

## Task 1: sse-starlette 依存追加

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: `sse-starlette` を依存に追加する**

`pyproject.toml` の `dependencies` リストに追加する:

```toml
dependencies = [
    "fastapi>=0.136",
    "uvicorn[standard]>=0.46",
    "python-multipart>=0.0.26",
    "pygit2>=1.19",
    "watchdog>=6.0",
    "jinja2>=3.1",
    "sqlmodel>=0.0.38",
    "pywebview>=6.2",
    "httpx>=0.28",
    "sse-starlette>=2.1",
]
```

- [ ] **Step 2: 依存をインストールする**

```bash
uv sync
```

期待: エラーなく完了する

- [ ] **Step 3: インポート確認**

```bash
uv run python -c "from sse_starlette.sse import EventSourceResponse; print('OK')"
```

期待出力: `OK`

- [ ] **Step 4: コミット**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: sse-starlette 依存を追加する"
```

---

## Task 2: EventBus 実装

**Files:**
- Create: `backend/services/event_bus.py`
- Test: `tests/unit/test_event_bus.py`

- [ ] **Step 1: テストファイルを作成する**

`tests/unit/test_event_bus.py` を作成:

```python
"""EventBus の単体テスト。"""

import asyncio

import pytest

from backend.services.event_bus import EventBus


def test_notify_後に_subscribe_がイベントを受け取る():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)
        received: list[str] = []

        async def collect():
            async for ev in bus.subscribe("repo1"):
                received.append(ev)
                return

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        bus.notify("repo1")
        await task
        return received

    # --- Act ---
    result = asyncio.run(_run())

    # --- Assert ---
    assert result == ["reload"]


def test_購読者なし時に_notify_がエラーにならない():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)
        bus.notify("no-subscriber")  # エラーにならないことを確認

    # --- Act / Assert ---
    asyncio.run(_run())  # 例外が出なければ OK


def test_複数購読者に全員ブロードキャストされる():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)
        results_a: list[str] = []
        results_b: list[str] = []

        async def collect_a():
            async for ev in bus.subscribe("repo1"):
                results_a.append(ev)
                return

        async def collect_b():
            async for ev in bus.subscribe("repo1"):
                results_b.append(ev)
                return

        task_a = asyncio.create_task(collect_a())
        task_b = asyncio.create_task(collect_b())
        await asyncio.sleep(0)
        bus.notify("repo1")
        await asyncio.gather(task_a, task_b)
        return results_a, results_b

    # --- Act ---
    a, b = asyncio.run(_run())

    # --- Assert ---
    assert a == ["reload"]
    assert b == ["reload"]


def test_異なる_repo_id_には通知されない():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)
        received: list[str] = []

        async def collect():
            async for ev in bus.subscribe("repo-A"):
                received.append(ev)
                return

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        bus.notify("repo-B")   # 別の repo_id に通知
        bus.notify("repo-A")   # 正しい repo_id に通知
        await task
        return received

    # --- Act ---
    result = asyncio.run(_run())

    # --- Assert ---
    assert result == ["reload"]
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_event_bus.py -v
```

期待: `ImportError: cannot import name 'EventBus' from 'backend.services.event_bus'`

- [ ] **Step 3: `EventBus` を実装する**

`backend/services/event_bus.py` を作成:

```python
"""リポジトリ更新イベントのバス。watchdog スレッドと asyncio の橋渡し。"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import AsyncGenerator


class EventBus:
    """repo_id ごとの購読者に更新イベントをブロードキャストする。"""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[str]]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """asyncio ループを登録する。lifespan 起動時に呼ぶこと。

        Args:
            loop: FastAPI が動作する asyncio ループ。
        """
        self._loop = loop

    def notify(self, repo_id: str) -> None:
        """watchdog スレッドから呼ぶ。購読者全員に "reload" を通知する。

        Args:
            repo_id: 更新があったリポジトリ ID。
        """
        if self._loop is None:
            return
        for q in self._queues.get(repo_id, []):
            self._loop.call_soon_threadsafe(q.put_nowait, "reload")

    async def subscribe(self, repo_id: str) -> AsyncGenerator[str, None]:
        """SSE エンドポイントが await する非同期ジェネレータ。

        Args:
            repo_id: 購読するリポジトリ ID。

        Yields:
            イベント文字列（現在は "reload" のみ）。
        """
        q: asyncio.Queue[str] = asyncio.Queue()
        self._queues[repo_id].append(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            self._queues[repo_id].remove(q)


event_bus = EventBus()
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_event_bus.py -v
```

期待: 4 件全て PASSED

- [ ] **Step 5: コミット**

```bash
git add backend/services/event_bus.py tests/unit/test_event_bus.py
git commit -m "feat: EventBus を実装する"
```

---

## Task 3: WatchService 実装

**Files:**
- Create: `backend/services/watch_service.py`
- Test: `tests/unit/test_watch_service.py`

- [ ] **Step 1: テストファイルを作成する**

`tests/unit/test_watch_service.py` を作成:

```python
"""WatchService と GitEventHandler の単体テスト。"""

import time
import uuid
from unittest.mock import MagicMock, patch

import pygit2
import pytest
from watchdog.events import FileCreatedEvent, FileModifiedEvent

from backend.services.event_bus import EventBus
from backend.services.watch_service import GitEventHandler, WatchService


@pytest.fixture()
def event_bus():
    """テスト用 EventBus（ループなし）。"""
    return EventBus()


@pytest.fixture()
def mock_engine():
    """テスト用ダミーエンジン。"""
    return MagicMock()


def test_on_modified_後にデバウンスが経過すると_sync_が呼ばれる(
    tmp_path, event_bus, mock_engine
):
    # --- Arrange ---
    call_count = 0

    class CountingHandler(GitEventHandler):
        def _sync(self) -> None:
            nonlocal call_count
            call_count += 1

    handler = CountingHandler("repo1", str(tmp_path), event_bus, mock_engine)

    # --- Act ---
    handler.on_modified(FileModifiedEvent(str(tmp_path / ".git" / "HEAD")))
    time.sleep(0.7)  # デバウンス 500ms を超えて待つ

    # --- Assert ---
    assert call_count == 1


def test_連続イベントはデバウンスで1回にまとまる(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    call_count = 0

    class CountingHandler(GitEventHandler):
        def _sync(self) -> None:
            nonlocal call_count
            call_count += 1

    handler = CountingHandler("repo1", str(tmp_path), event_bus, mock_engine)

    # --- Act ---
    handler.on_modified(FileModifiedEvent(str(tmp_path / ".git" / "HEAD")))
    handler.on_modified(FileModifiedEvent(str(tmp_path / ".git" / "refs")))
    handler.on_created(FileCreatedEvent(str(tmp_path / ".git" / "refs" / "heads" / "main")))
    time.sleep(0.7)

    # --- Assert ---
    assert call_count == 1


def test_sync_が_sync_repository_を呼ぶ(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    repo_id = str(uuid.uuid4())
    handler = GitEventHandler(repo_id, str(repo_path), event_bus, mock_engine)

    with patch("backend.services.watch_service.sync_repository") as mock_sync:
        # --- Act ---
        handler._sync()

        # --- Assert ---
        mock_sync.assert_called_once()
        call_args = mock_sync.call_args
        assert call_args.args[1] == repo_id
        assert call_args.args[2] == str(repo_path)


def test_sync_後に_event_bus_notify_が呼ばれる(tmp_path, mock_engine):
    # --- Arrange ---
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    repo_id = str(uuid.uuid4())
    bus = MagicMock(spec=EventBus)
    handler = GitEventHandler(repo_id, str(repo_path), bus, mock_engine)

    with patch("backend.services.watch_service.sync_repository"):
        # --- Act ---
        handler._sync()

        # --- Assert ---
        bus.notify.assert_called_once_with(repo_id)


def test_sync_失敗時に_notify_を呼ばない(tmp_path, mock_engine):
    # --- Arrange ---
    repo_id = str(uuid.uuid4())
    bus = MagicMock(spec=EventBus)
    handler = GitEventHandler(repo_id, str(tmp_path), bus, mock_engine)

    with patch(
        "backend.services.watch_service.sync_repository",
        side_effect=Exception("Git error"),
    ):
        # --- Act ---
        handler._sync()

        # --- Assert ---
        bus.notify.assert_not_called()


def test_watch_service_同一パスの二重登録を防ぐ(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    svc = WatchService(event_bus, mock_engine)

    # --- Act ---
    svc.watch("r1", str(tmp_path))
    svc.watch("r1", str(tmp_path))  # 同じパスを再登録

    # --- Assert ---
    assert len(svc._watched_paths) == 1
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_watch_service.py -v
```

期待: `ImportError: cannot import name 'GitEventHandler' from 'backend.services.watch_service'`

- [ ] **Step 3: `WatchService` と `GitEventHandler` を実装する**

`backend/services/watch_service.py` を作成:

```python
"""watchdog Observer によるリポジトリ監視サービス。"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from sqlmodel import Session
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from backend.services.event_bus import EventBus
from backend.services.sync_service import sync_repository

_logger = logging.getLogger(__name__)


class GitEventHandler(FileSystemEventHandler):
    """`.git` ディレクトリの変化を検知して同期をトリガーする。"""

    _DEBOUNCE_SEC = 0.5

    def __init__(
        self,
        repo_id: str,
        repo_path: str,
        event_bus: EventBus,
        engine: object,
    ) -> None:
        super().__init__()
        self._repo_id = repo_id
        self._repo_path = repo_path
        self._event_bus = event_bus
        self._engine = engine
        self._timer: threading.Timer | None = None

    def on_modified(self, event: FileSystemEvent) -> None:
        """ファイル変更イベントを受け取りデバウンスする。"""
        self._debounce()

    def on_created(self, event: FileSystemEvent) -> None:
        """ファイル作成イベントを受け取りデバウンスする。"""
        self._debounce()

    def _debounce(self) -> None:
        """連続イベントをまとめて 1 回の同期にする。"""
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self._DEBOUNCE_SEC, self._sync)
        self._timer.start()

    def _sync(self) -> None:
        """同期を実行し、完了後にイベントバスへ通知する。"""
        try:
            with Session(self._engine) as session:  # type: ignore[call-overload]
                sync_repository(session, self._repo_id, self._repo_path)
        except Exception:
            _logger.exception("リポジトリ同期中にエラーが発生しました: %s", self._repo_id)
            return
        self._event_bus.notify(self._repo_id)


class WatchService:
    """watchdog Observer を管理し、リポジトリの監視を制御する。"""

    def __init__(self, event_bus: EventBus, engine: object) -> None:
        self._event_bus = event_bus
        self._engine = engine
        self._observer = Observer()
        self._watched_paths: set[str] = set()

    def watch(self, repo_id: str, repo_path: str) -> None:
        """リポジトリの `.git` ディレクトリを監視対象に追加する。

        Args:
            repo_id: リポジトリ ID。
            repo_path: Git 作業ディレクトリのパス。
        """
        git_dir = str(Path(repo_path) / ".git")
        if git_dir in self._watched_paths:
            return
        handler = GitEventHandler(repo_id, repo_path, self._event_bus, self._engine)
        self._observer.schedule(handler, git_dir, recursive=True)
        self._watched_paths.add(git_dir)

    def start(self) -> None:
        """Observer を起動する。lifespan startup で呼ぶ。"""
        self._observer.start()

    def stop(self) -> None:
        """Observer を停止し、スレッド終了を待つ。lifespan shutdown で呼ぶ。"""
        self._observer.stop()
        self._observer.join()
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_watch_service.py -v
```

期待: 7 件全て PASSED（デバウンステストは各 700ms かかるため合計数秒）

- [ ] **Step 5: コミット**

```bash
git add backend/services/watch_service.py tests/unit/test_watch_service.py
git commit -m "feat: WatchService と GitEventHandler を実装する"
```

---

## Task 4: SSE エンドポイント実装

**Files:**
- Create: `backend/routers/graph_events.py`
- Test: `tests/unit/test_graph_events.py`

- [ ] **Step 1: テストファイルを作成する**

`tests/unit/test_graph_events.py` を作成:

```python
"""graph_events ルーターの単体テスト。"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.services.event_bus import EventBus


@pytest.fixture()
def app_with_events():
    """テスト用 FastAPI アプリ（EventBus 付き）。"""
    from backend.routers.graph_events import make_router

    bus = EventBus()
    test_app = FastAPI()
    test_app.include_router(make_router(bus))
    return test_app, bus


def test_events_エンドポイントが_text_event_stream_を返す(app_with_events):
    # --- Arrange ---
    app, _ = app_with_events
    client = TestClient(app, raise_server_exceptions=False)

    # --- Act ---
    with client.stream("GET", "/repos/00000000-0000-0000-0000-000000000001/events") as r:
        # --- Assert ---
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


def test_events_無効な_repo_id_は_404_を返す(app_with_events):
    # --- Arrange ---
    app, _ = app_with_events
    client = TestClient(app, raise_server_exceptions=False)

    # --- Act ---
    r = client.get("/repos/not-a-valid-uuid/events")

    # --- Assert ---
    assert r.status_code == 404
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_graph_events.py -v
```

期待: `ImportError: cannot import name 'make_router'`

- [ ] **Step 3: `graph_events` ルーターを実装する**

`backend/routers/graph_events.py` を作成:

```python
"""グラフ更新 SSE エンドポイント。"""

from __future__ import annotations

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from backend.services.event_bus import EventBus
from backend.validation import parse_repo_id


def make_router(event_bus: EventBus) -> APIRouter:
    """EventBus を注入したルーターを返す。

    Args:
        event_bus: イベントバスのインスタンス。

    Returns:
        FastAPI ルーター。
    """
    router = APIRouter(tags=["graph-events"])

    @router.get("/repos/{repo_id}/events")
    async def graph_events(repo_id: str) -> EventSourceResponse:
        """グラフ更新 SSE ストリームを返す。変化があると event: reload を送信する。"""
        rid = parse_repo_id(repo_id)

        async def _generate():
            async for _ in event_bus.subscribe(rid):
                yield {"event": "reload", "data": ""}

        return EventSourceResponse(_generate())

    return router
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_graph_events.py -v
```

期待: 2 件全て PASSED

- [ ] **Step 5: コミット**

```bash
git add backend/routers/graph_events.py tests/unit/test_graph_events.py
git commit -m "feat: グラフ更新 SSE エンドポイントを追加する"
```

---

## Task 5: main.py と api.py の更新

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/routers/api.py`

- [ ] **Step 1: `main.py` を更新する**

`backend/main.py` を以下の内容に置き換える:

```python
"""FastAPI アプリケーションのエントリポイント。"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from backend.db import create_db_and_tables, engine
from backend.repositories import cache_repo
from backend.routers import api, html, update
from backend.routers.graph_events import make_router
from backend.services.event_bus import event_bus
from backend.services.watch_service import WatchService

ROOT = Path(__file__).resolve().parent.parent


def _start_watch_service(app: FastAPI) -> WatchService:
    """既存リポジトリを全て監視する WatchService を起動する。"""
    loop = asyncio.get_running_loop()
    event_bus.set_loop(loop)
    watch_svc = WatchService(event_bus, engine)
    with Session(engine) as session:
        for repo in cache_repo.list_repositories(session):
            watch_svc.watch(repo.id, repo.path)
    watch_svc.start()
    app.state.watch_service = watch_svc
    return watch_svc


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時にテーブル作成と監視サービスを起動する。"""
    create_db_and_tables()
    watch_svc = _start_watch_service(app)
    yield
    watch_svc.stop()


app = FastAPI(title="Git Lanes", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.include_router(html.router)
app.include_router(api.router)
app.include_router(update.router)
app.include_router(make_router(event_bus))


@app.get("/health")
async def health_check() -> dict[str, str]:
    """サーバーの稼働確認用エンドポイント。"""
    return {"status": "ok"}
```

- [ ] **Step 2: `api.py` を更新する**

`backend/routers/api.py` を以下の内容に置き換える:

```python
"""登録などの HTTP API。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

import pygit2
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backend.db import get_session
from backend.repositories import cache_repo
from backend.repositories.git_repo import open_repository
from backend.services.watch_service import WatchService

router = APIRouter(tags=["api"])


def _get_watch_service(request: Request) -> WatchService:
    """app.state から WatchService を取り出す。"""
    return request.app.state.watch_service  # type: ignore[no-any-return]


@router.post("/api/repos")
async def register_repository(
    request: Request,
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
    existing = cache_repo.get_repository_by_path(session, str(resolved))
    if existing is not None:
        _get_watch_service(request).watch(existing.id, existing.path)
        return RedirectResponse(url=f"/repos/{existing.id}/graph", status_code=303)
    try:
        cache_repo.insert_repository(session, repo_id, str(resolved), resolved.name)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="このパスは既に登録されています") from exc
    _get_watch_service(request).watch(repo_id, str(resolved))
    return RedirectResponse(url=f"/repos/{repo_id}/graph", status_code=303)
```

- [ ] **Step 3: lint と型チェックを実行する**

```bash
uv run task lint && uv run task typecheck
```

期待: エラーなし（警告があれば修正する）

- [ ] **Step 4: 既存テストが通ることを確認する**

```bash
uv run pytest tests/unit/ -v
```

期待: 全件 PASSED（新規テストを含む）

- [ ] **Step 5: コミット**

```bash
git add backend/main.py backend/routers/api.py
git commit -m "feat: lifespan に WatchService を組み込み、リポジトリ登録時に監視を開始する"
```

---

## Task 6: graph.html と base.html の更新

**Files:**
- Modify: `backend/templates/base.html`
- Modify: `backend/templates/graph.html`

- [ ] **Step 1: `base.html` に htmx SSE 拡張スクリプトを追加する**

`backend/templates/base.html` の `</head>` 直前に SSE 拡張スクリプトを追加する。
変更前:
```html
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <script src="https://unpkg.com/hyperscript.org@0.9.14"></script>
</head>
```

変更後:
```html
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <script src="https://unpkg.com/htmx-ext-sse@2.2.2/sse.js"></script>
  <script src="https://unpkg.com/hyperscript.org@0.9.14"></script>
</head>
```

- [ ] **Step 2: `graph.html` に SSE 接続タグを追加する**

`{% block body %}` の直後（`<div id="commit-tooltip"` の前）に SSE 接続タグを追加する。
変更前の該当箇所:
```html
{% block body %}
<div id="commit-tooltip"
```

変更後:
```html
{% block body %}
<div
  hx-ext="sse"
  sse-connect="/repos/{{ repo_id }}/events"
  _="on sse:reload call window.location.reload()"
></div>
<div id="commit-tooltip"
```

- [ ] **Step 3: 開発サーバーを起動して動作確認する**

```bash
uv run task dev
```

ブラウザで `http://localhost:8000` を開き、リポジトリを選択してグラフを表示する。
別ターミナルで監視対象リポジトリに対して `git commit` を実行し、グラフが自動リロードされることを確認する。

```bash
# 別ターミナル（監視対象リポジトリで）
cd /path/to/watched/repo
echo "test" >> test.txt
git add test.txt
git commit -m "test: 自動リロード確認"
```

期待: 3 秒以内にグラフ画面が自動リロードされ、新しいコミットが表示される

- [ ] **Step 4: 全テストを実行する**

```bash
uv run task test
```

期待: 全件 PASSED

- [ ] **Step 5: コミット**

```bash
git add backend/templates/base.html backend/templates/graph.html
git commit -m "feat: グラフ画面に SSE 自動リロードを追加する"
```

---

## Task 7: 品質チェック & 最終コミット

**Files:** なし（チェックのみ）

- [ ] **Step 1: lint を実行する**

```bash
uv run task lint
```

期待: エラーなし

- [ ] **Step 2: 型チェックを実行する**

```bash
uv run task typecheck
```

期待: エラーなし

- [ ] **Step 3: 全テストをカバレッジ付きで実行する**

```bash
uv run pytest tests/unit/ --cov=backend --cov-report=term-missing -v
```

期待: 全件 PASSED、カバレッジ 85% 以上

- [ ] **Step 4: ファイル行数の制約確認**

```bash
find backend -name "*.py" ! -path "*/templates/*" | xargs wc -l | sort -rn | head -20
```

期待: `backend/services/watch_service.py`・`backend/services/event_bus.py`・`backend/routers/graph_events.py` が各 150 行以内
