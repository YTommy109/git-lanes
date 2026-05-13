# ウィンドウ状態永続化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** アプリ終了前のウィンドウ位置・サイズ・表示リポジトリ・アクティブコミットを JSON に保存し、次回起動時に復元する。

**Architecture:** `state_store.py` が `WindowState` dataclass と load/save/update API を提供する。pywebview の moved/resized イベントでウィンドウ座標をデバウンス保存し、FastAPI ハンドラーの副作用でリポジトリ・コミット状態を保存する。起動時に保存済み状態から初期 URL と create_window() 引数を構築する。

**Tech Stack:** Python 3.12, pywebview 6.x, FastAPI, Jinja2, hyperscript

---

## ファイル変更一覧

| ファイル | 種別 | 責務 |
|---|---|---|
| `backend/paths.py` | 修正 | `window_state_path()` を追加 |
| `backend/state_store.py` | 新規 | `WindowState` dataclass, `load()`, `save()`, `update()` |
| `backend/app.py` | 修正 | 状態読み込み・pywebview イベント登録・デバウンス保存 |
| `backend/routers/html.py` | 修正 | `graph_page` / `commit_detail` で状態保存、`active_commit` パラメータ |
| `backend/templates/graph.html` | 修正 | コミットノードに `id` 追加、hyperscript スクロール |
| `tests/unit/test_paths.py` | 修正 | `window_state_path` のテスト追加 |
| `tests/unit/test_state_store.py` | 新規 | `state_store` の全テスト |
| `tests/unit/test_html_state.py` | 新規 | `html.py` ハンドラーの状態保存テスト |

---

## Task 1: `paths.py` に `window_state_path()` を追加する

**Files:**
- Modify: `backend/paths.py`
- Test: `tests/unit/test_paths.py`

- [ ] **Step 1: テストを追加して失敗させる**

`tests/unit/test_paths.py` の末尾に追加：

```python
from backend.paths import data_dir, window_state_path


def test_window_state_path_は_data_dir_配下を返す(tmp_path, monkeypatch):
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))

    # --- Act ---
    result = window_state_path()

    # --- Assert ---
    assert result == tmp_path.resolve() / "window_state.json"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_paths.py::test_window_state_path_は_data_dir_配下を返す -v
```

期待: `ImportError: cannot import name 'window_state_path'`

- [ ] **Step 3: `window_state_path()` を実装する**

`backend/paths.py` の末尾に追加：

```python
def window_state_path() -> Path:
    """ウィンドウ状態 JSON ファイルのパスを返す。

    Returns:
        ``{data_dir}/window_state.json``。
    """
    return data_dir() / "window_state.json"
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_paths.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: コミットする**

```bash
git add backend/paths.py tests/unit/test_paths.py
git commit -m "feat: paths に window_state_path() を追加する"
```

---

## Task 2: `state_store.py` を新規作成する

**Files:**
- Create: `backend/state_store.py`
- Create: `tests/unit/test_state_store.py`

- [ ] **Step 1: テストファイルを作成して失敗させる**

`tests/unit/test_state_store.py` を新規作成：

```python
"""state_store の単体テスト。"""

import json

import pytest

from backend.state_store import WindowState, load, save, update


def test_load_はファイル不在のときデフォルト値を返す(tmp_path):
    # --- Arrange ---
    path = tmp_path / "window_state.json"

    # --- Act ---
    result = load(path)

    # --- Assert ---
    assert isinstance(result, WindowState)
    assert result.width == 1280
    assert result.height == 800
    assert result.x is None
    assert result.repo_id is None


def test_load_は壊れた_json_のときデフォルト値を返す(tmp_path):
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    path.write_text("not valid json", encoding="utf-8")

    # --- Act ---
    result = load(path)

    # --- Assert ---
    assert isinstance(result, WindowState)
    assert result.width == 1280


def test_load_は保存済みの値を返す(tmp_path):
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    path.write_text(
        json.dumps({"x": 100, "y": 200, "width": 1400, "height": 900}),
        encoding="utf-8",
    )

    # --- Act ---
    result = load(path)

    # --- Assert ---
    assert result.x == 100
    assert result.y == 200
    assert result.width == 1400
    assert result.height == 900


def test_save_は_json_ファイルに書き込む(tmp_path):
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    state = WindowState(x=10, y=20, width=800, height=600)

    # --- Act ---
    save(path, state)

    # --- Assert ---
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["x"] == 10
    assert data["width"] == 800


def test_round_trip_で値が一致する(tmp_path):
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    original = WindowState(
        x=50, y=60, width=1920, height=1080,
        repo_id="abc", commit_hash="a" * 40,
        show_remote=False, show_tags=True,
    )

    # --- Act ---
    save(path, original)
    restored = load(path)

    # --- Assert ---
    assert restored.x == 50
    assert restored.width == 1920
    assert restored.repo_id == "abc"
    assert restored.commit_hash == "a" * 40
    assert restored.show_remote is False


def test_update_は指定フィールドのみ上書きする(tmp_path):
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    initial = WindowState(x=10, y=20, width=1280, height=800, repo_id="old")
    save(path, initial)

    # --- Act ---
    update(path, repo_id="new", show_remote=False)

    # --- Assert ---
    result = load(path)
    assert result.repo_id == "new"
    assert result.show_remote is False
    assert result.x == 10  # 変更していないフィールドは保たれる
    assert result.width == 1280
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_state_store.py -v
```

期待: `ModuleNotFoundError: No module named 'backend.state_store'`

- [ ] **Step 3: `state_store.py` を実装する**

`backend/state_store.py` を新規作成：

```python
"""ウィンドウ状態の永続化。"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

_logger = logging.getLogger(__name__)
_lock = threading.Lock()


@dataclass
class WindowState:
    """保存するウィンドウ状態。"""

    x: int | None = None
    y: int | None = None
    width: int = 1280
    height: int = 800
    repo_id: str | None = None
    commit_hash: str | None = None
    show_remote: bool = True
    show_tags: bool = True


_FIELDS = frozenset(WindowState.__dataclass_fields__)


def load(path: Path) -> WindowState:
    """JSON からウィンドウ状態を読み込む。

    Args:
        path: JSON ファイルパス。

    Returns:
        保存済みの状態。ファイルが存在しないか壊れている場合はデフォルト値。
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return WindowState(**{k: v for k, v in data.items() if k in _FIELDS})
    except Exception:
        return WindowState()


def save(path: Path, state: WindowState) -> None:
    """ウィンドウ状態を JSON にアトミックに書き込む。

    Args:
        path: 書き込み先 JSON ファイルパス。
        state: 保存するウィンドウ状態。
    """
    with _lock:
        _write(path, state)


def update(path: Path, **fields: object) -> None:
    """指定フィールドだけ上書きして保存する。

    Args:
        path: JSON ファイルパス。
        **fields: 更新するフィールド名と値。
    """
    with _lock:
        state = load(path)
        for k, v in fields.items():
            if hasattr(state, k):
                setattr(state, k, v)
        _write(path, state)


def _write(path: Path, state: WindowState) -> None:
    """JSON にアトミックに書き込む（呼び出し元がロックを保持していること）。"""
    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(
            json.dumps(asdict(state), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
    except OSError:
        _logger.warning("ウィンドウ状態の保存に失敗しました: %s", path)
```

- [ ] **Step 4: テストが全て通ることを確認する**

```bash
uv run pytest tests/unit/test_state_store.py -v
```

期待: 全 6 テスト PASS

- [ ] **Step 5: Lint を通す**

```bash
uv run task lint
```

期待: エラーなし

- [ ] **Step 6: コミットする**

```bash
git add backend/state_store.py tests/unit/test_state_store.py
git commit -m "feat: WindowState の永続化モジュールを追加する"
```

---

## Task 3: `app.py` にウィンドウ状態の読み込みと保存を追加する

**Files:**
- Modify: `backend/app.py`
- Create: `tests/unit/test_app_state.py`

- [ ] **Step 1: `_build_initial_url` のテストを作成して失敗させる**

`tests/unit/test_app_state.py` を新規作成：

```python
"""app.py のウィンドウ状態関連ユーティリティのテスト。"""

from backend.app import _build_initial_url
from backend.state_store import WindowState


def test_build_initial_url_はリポジトリ未保存のときルートを返す():
    # --- Arrange ---
    state = WindowState()

    # --- Act ---
    result = _build_initial_url(8000, state)

    # --- Assert ---
    assert result == "http://127.0.0.1:8000/"


def test_build_initial_url_はリポジトリ保存済みのときグラフ画面を返す():
    # --- Arrange ---
    state = WindowState(repo_id="abc-123", show_remote=True, show_tags=False)

    # --- Act ---
    result = _build_initial_url(8000, state)

    # --- Assert ---
    assert "/repos/abc-123/graph" in result
    assert "show_tags=false" in result


def test_build_initial_url_はコミットハッシュを含める():
    # --- Arrange ---
    h = "a" * 40
    state = WindowState(repo_id="abc-123", commit_hash=h)

    # --- Act ---
    result = _build_initial_url(8000, state)

    # --- Assert ---
    assert f"active_commit={h}" in result
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_app_state.py -v
```

期待: `ImportError: cannot import name '_build_initial_url'`

- [ ] **Step 3: `app.py` を更新する**

`backend/app.py` を以下の内容に書き換える：

```python
"""pywebview アプリケーションのエントリポイント。"""

import os
import socket
import threading
import time

import uvicorn
import webview

from backend import paths, state_store
from backend.state_store import WindowState

# アプリモードを宣言してからバックエンドをインポートさせる（ログレベルが INFO になる）
# uvicorn.run は文字列で "backend.main:app" を受けるので実行時まで main はインポートされない
os.environ.setdefault("GIT_LANES_MODE", "app")

HOST = "127.0.0.1"

_save_timer: threading.Timer | None = None
_timer_lock = threading.Lock()


def _find_free_port() -> int:
    """OS に空きポートを割り当ててもらう。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _start_server(port: int) -> None:
    """バックグラウンドスレッドで uvicorn を起動する。"""
    uvicorn.run("backend.main:app", host=HOST, port=port, log_level="warning")


def _wait_for_server(port: int, timeout: float = 10.0) -> bool:
    """サーバーが応答するまで待機する。

    Args:
        port: 待機するポート番号。
        timeout: 最大待機秒数。

    Returns:
        サーバーが起動したら True、タイムアウトなら False。
    """
    import urllib.request

    url = f"http://{HOST}:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _build_initial_url(port: int, state: WindowState) -> str:
    """保存済み状態から初期 URL を構築する。

    Args:
        port: FastAPI が Listen しているポート番号。
        state: 保存済みウィンドウ状態。

    Returns:
        webview.create_window() に渡す URL 文字列。
    """
    if state.repo_id is None:
        return f"http://{HOST}:{port}/"
    remote = str(state.show_remote).lower()
    tags = str(state.show_tags).lower()
    url = f"http://{HOST}:{port}/repos/{state.repo_id}/graph?show_remote={remote}&show_tags={tags}"
    if state.commit_hash:
        url += f"&active_commit={state.commit_hash}"
    return url


def _schedule_save(path: object, state: WindowState) -> None:
    """デバウンスしてウィンドウ状態を保存する（500ms 後に書き込み）。"""
    global _save_timer
    with _timer_lock:
        if _save_timer is not None:
            _save_timer.cancel()
        _save_timer = threading.Timer(0.5, state_store.save, (path, state))
        _save_timer.daemon = True
        _save_timer.start()


def main() -> None:
    """pywebview アプリを起動する。"""
    path = paths.window_state_path()
    state = state_store.load(path)

    port = _find_free_port()
    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()

    if not _wait_for_server(port):
        raise RuntimeError("サーバーの起動がタイムアウトしました。")

    win = webview.create_window(
        title="Git Lanes",
        url=_build_initial_url(port, state),
        width=state.width,
        height=state.height,
        x=state.x,
        y=state.y,
        resizable=True,
    )

    def on_moved(x: int, y: int) -> None:
        state.x = int(x)
        state.y = int(y)
        _schedule_save(path, state)

    def on_resized(width: int, height: int) -> None:
        state.width = int(width)
        state.height = int(height)
        _schedule_save(path, state)

    win.events.moved += on_moved
    win.events.resized += on_resized
    webview.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_app_state.py -v
```

期待: 全 3 テスト PASS

- [ ] **Step 5: Lint を通す**

```bash
uv run task lint
```

期待: エラーなし

- [ ] **Step 6: コミットする**

```bash
git add backend/app.py tests/unit/test_app_state.py
git commit -m "feat: app.py にウィンドウ状態の読み込みと保存を追加する"
```

---

## Task 4: `html.py` でリポジトリ・コミット状態を保存し `active_commit` を復元する

**Files:**
- Modify: `backend/routers/html.py`
- Create: `tests/unit/test_html_state.py`

- [ ] **Step 1: テストファイルを作成して失敗させる**

`tests/unit/test_html_state.py` を新規作成：

```python
"""html.py ハンドラーの状態保存テスト。"""

import time
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.db import get_session
from backend.main import app
from backend.models import Branch, Commit
from backend.repositories.repository_repo import insert_repository

REPO_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
COMMIT_HASH = "a" * 40


@pytest.fixture()
def client(session: Session):
    """TestClient with in-memory DB。state_store.update はモック化する。"""
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(session: Session, tmp_path):
    """テスト用リポジトリとコミットを DB に挿入する。"""
    insert_repository(session, REPO_ID, str(tmp_path), "test-repo")
    session.add(Commit(
        hash=COMMIT_HASH,
        short_hash=COMMIT_HASH[:7],
        message="test commit",
        author_name="tester",
        author_email="t@t.com",
        committed_at=int(time.time()),
        repo_id=REPO_ID,
    ))
    session.add(Branch(name="main", repo_id=REPO_ID, tip_hash=COMMIT_HASH))
    session.commit()


def _dummy_graph():
    """graph_service.sync_and_build のダミー戻り値。"""
    return SimpleNamespace(
        nodes=[], edges=[], branch_headers=[], canvas_width=100, canvas_height=100
    )


def test_graph_page_はリポジトリ状態を保存する(client, seeded):
    # --- Arrange ---
    with patch("backend.routers.html.state_store.update") as mock_update, \
         patch("backend.services.graph_service.sync_and_build", return_value=_dummy_graph()):

        # --- Act ---
        client.get(f"/repos/{REPO_ID}/graph?show_remote=true&show_tags=false")

    # --- Assert ---
    mock_update.assert_called_once_with(
        ANY, repo_id=REPO_ID, show_remote=True, show_tags=False
    )


def test_commit_detail_はコミットハッシュを保存する(client, seeded):
    # --- Arrange ---
    with patch("backend.routers.html.state_store.update") as mock_update:

        # --- Act ---
        client.get(f"/repos/{REPO_ID}/commits/{COMMIT_HASH}/detail")

    # --- Assert ---
    mock_update.assert_called_once_with(ANY, commit_hash=COMMIT_HASH)


def test_graph_page_は_active_commit_で詳細パネルを描画する(client, seeded):
    # --- Arrange ---
    with patch("backend.routers.html.state_store.update"), \
         patch("backend.services.graph_service.sync_and_build", return_value=_dummy_graph()):

        # --- Act ---
        resp = client.get(f"/repos/{REPO_ID}/graph?active_commit={COMMIT_HASH}")

    # --- Assert ---
    assert resp.status_code == 200
    assert "test commit" in resp.text  # 詳細パネルにコミットメッセージが含まれる
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_html_state.py -v
```

期待: 3 テスト失敗（状態ファイルが作られない、active_commit が無視される）

- [ ] **Step 3: `html.py` を更新する**

`backend/routers/html.py` を以下の内容に書き換える：

```python
# backend/routers/html.py
"""HTML 応答（htmx 向け）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from backend import paths, state_store
from backend.db import get_session
from backend.exceptions import CommitNotFoundError, RepositoryNotFoundError
from backend.jinja import templates
from backend.models import Commit
from backend.repositories import commit_repo, repository_repo, tag_repo
from backend.services import graph_service
from backend.validation import parse_commit_hash, parse_repo_id

router = APIRouter(tags=["html"])
_logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse)
async def welcome(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ウェルカム画面を返す。"""
    repos = repository_repo.list_repositories(session)
    return templates.TemplateResponse(
        request, "welcome.html", {"repos": repos, "current_repo_id": None}
    )


@router.get("/repos/{repo_id}/graph", response_class=HTMLResponse)
async def graph_page(
    request: Request,
    repo_id: str,
    show_remote: bool = True,
    show_tags: bool = True,
    active_commit: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ブランチグラフ画面を返す。"""
    rid = parse_repo_id(repo_id)
    rec = repository_repo.get_repository(session, rid)
    if rec is None:
        raise RepositoryNotFoundError
    result = graph_service.sync_and_build(
        session, rid, rec.path, show_remote=show_remote, show_tags=show_tags
    )
    state_store.update(
        paths.window_state_path(),
        repo_id=rid,
        show_remote=show_remote,
        show_tags=show_tags,
    )
    detail_commit, detail_tags = _fetch_active_detail(session, rid, active_commit)
    context: dict = {
        "repo_id": rid,
        "repo_name": rec.name,
        "nodes": result.nodes,
        "edges": result.edges,
        "branch_headers": result.branch_headers,
        "svg_width": result.canvas_width,
        "svg_height": result.canvas_height,
        "repos": repository_repo.list_repositories(session),
        "current_repo_id": rid,
        "show_remote": show_remote,
        "show_tags": show_tags,
        "active_commit": active_commit,
        "active_detail_commit": detail_commit,
        "active_detail_tags": detail_tags,
    }
    return templates.TemplateResponse(request, "graph.html", context)


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
    row = commit_repo.get_commit(session, rid, ch)
    if row is None:
        raise CommitNotFoundError
    tags = tag_repo.get_tags_for_commit(session, rid, ch)
    state_store.update(paths.window_state_path(), commit_hash=ch)
    return templates.TemplateResponse(
        request, "partials/detail.html", {"commit": row, "tags": tags}
    )


def _fetch_active_detail(
    session: Session, repo_id: str, active_commit: str | None
) -> tuple[Commit | None, list[str]]:
    """active_commit が有効なコミットハッシュならその詳細を返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        active_commit: クエリパラメータで渡されたコミットハッシュ（未検証）。

    Returns:
        (Commit オブジェクト, タグリスト)。無効な場合は (None, [])。
    """
    if active_commit is None:
        return None, []
    try:
        ch = parse_commit_hash(active_commit)
    except Exception:
        return None, []
    row = commit_repo.get_commit(session, repo_id, ch)
    if row is None:
        return None, []
    return row, tag_repo.get_tags_for_commit(session, repo_id, ch)
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_html_state.py -v
```

期待: 全 3 テスト PASS

- [ ] **Step 5: 既存テストも通ることを確認する**

```bash
uv run task test
```

期待: 全テスト PASS、カバレッジ 85% 以上

- [ ] **Step 6: コミットする**

```bash
git add backend/routers/html.py tests/unit/test_html_state.py
git commit -m "feat: graph_page と commit_detail に状態保存を追加する"
```

---

## Task 5: `graph.html` にコミット ID とスクロール復元を追加する

**Files:**
- Modify: `backend/templates/graph.html`

このタスクはテンプレートの変更のみで、単体テストより目視確認が主体。

- [ ] **Step 1: `<g class="commit-node">` に `id` を追加する**

`graph.html` の88行目付近にある `<g class="commit-node"` を探し、`id` 属性を追加する。

変更前（88行目）：
```html
          <g
            class="commit-node"
            data-lane="{{ node.lane }}"
```

変更後：
```html
          <g
            id="node-{{ node.commit.hash }}"
            class="commit-node"
            data-lane="{{ node.lane }}"
```

- [ ] **Step 2: 詳細パネルの初期描画ブロックを追加する**

`graph.html` の145行目付近にある以下のブロックを置き換える。

変更前：
```html
    <div id="commit-detail">
      <p class="-c:text-2">コミットを選択してください。</p>
    </div>
```

変更後：
```html
    <div id="commit-detail">
      {% if active_detail_commit %}
        {% with commit=active_detail_commit, tags=active_detail_tags %}
          {% include "partials/detail.html" %}
        {% endwith %}
      {% else %}
        <p class="-c:text-2">コミットを選択してください。</p>
      {% endif %}
    </div>
```

- [ ] **Step 3: スクロール復元の hyperscript を追加する**

`graph.html` の `<script src="/static/js/graph-keyboard.js"></script>` の直前に追加する：

変更前：
```html
<script src="/static/js/graph-keyboard.js"></script>
{% endblock %}
```

変更後：
```html
{% if active_commit %}
<div hidden
  _="on load
       set el to document.getElementById('node-{{ active_commit }}')
       if el then el.scrollIntoView({block: 'center'}) end">
</div>
{% endif %}
<script src="/static/js/graph-keyboard.js"></script>
{% endblock %}
```

- [ ] **Step 4: 開発サーバーで動作を目視確認する**

```bash
uv run task dev
```

ブラウザで `http://localhost:8000` を開き、リポジトリを表示してコミットをクリックする。その後 `http://localhost:8000/repos/{repo_id}/graph?active_commit={hash}` に直接アクセスして、詳細パネルが表示されることと、コミットが画面中央に表示されることを確認する。

- [ ] **Step 5: 全テストを通す**

```bash
uv run task test
```

期待: 全テスト PASS

- [ ] **Step 6: コミットする**

```bash
git add backend/templates/graph.html
git commit -m "feat: グラフにコミット ID とスクロール復元を追加する"
```

---

## 最終確認

- [ ] **全テスト + カバレッジ確認**

```bash
uv run task test
```

期待: 全テスト PASS、カバレッジ 85% 以上

- [ ] **Lint + 型チェック**

```bash
uv run task lint && uv run task typecheck
```

期待: エラーなし
