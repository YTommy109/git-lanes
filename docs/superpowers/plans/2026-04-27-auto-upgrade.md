# アプリ内自動アップデート機能 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub Releases API でバージョンを確認し、httpx で DMG を直接ダウンロードしてアプリを自動更新する機能を実装する

**Architecture:** FastAPI のサービス層でバージョンチェック・ダウンロード・インストールを担う。htmx の hx-trigger="load" でページロード時に更新確認を行い、ダウンロード進捗は 1秒ポーリングで表示する。インストール完了後は /tmp/git-lanes-updater.sh が旧アプリと差し替えてから再起動する。

**Tech Stack:** Python 3.12, FastAPI, httpx, htmx 2.x, hyperscript 0.9.x, Jinja2, subprocess (hdiutil)

---

## ファイルマップ

| パス | 新規/修正 | 役割 |
|---|---|---|
| `pyproject.toml` | 修正 | httpx を main 依存へ移動、バージョンを 0.1.4 に |
| `backend/services/update_service.py` | 新規 | GitHub API チェック・httpx ダウンロード・インストール |
| `backend/routers/update.py` | 新規 | 4つの API エンドポイント |
| `backend/main.py` | 修正 | update ルーターのインクルード |
| `backend/templates/base.html` | 修正 | バナー挿入スロット追加 |
| `backend/templates/partials/update_banner.html` | 新規 | 更新通知バナー + ダウンロードボタン |
| `backend/templates/partials/update_progress.html` | 新規 | 進捗バー（ポーリング） |
| `tests/unit/test_update_service.py` | 新規 | update_service の単体テスト |

---

## Task 1: pyproject.toml の更新（httpx 移動・バージョン 0.1.4）

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: httpx を dev から main 依存へ移動し、バージョンを 0.1.4 に変更する**

`pyproject.toml` の `[project]` → `dependencies` に `httpx>=0.28` を追加し、`[dependency-groups]` → `dev` から `httpx` 行を削除する。バージョンも変更する。

変更後の `[project]` セクション先頭:
```toml
[project]
name = "git-lanes"
version = "0.1.4"
requires-python = ">=3.12,<3.13"
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
]
```

変更後の `[dependency-groups]` セクション:
```toml
[dependency-groups]
dev = [
    "pytest",
    "pytest-cov",
    "pytest-playwright",
    "playwright",
    "taskipy",
    "ruff",
    "ty",
    "pre-commit",
    "pyinstaller>=6.20.0",
]
```

`[tool.bumpversion]` の `current_version` も更新する:
```toml
[tool.bumpversion]
current_version = "0.1.4"
```

- [ ] **Step 2: uv sync で uv.lock を更新する**

```bash
uv sync
```

期待: `uv.lock` が更新され、エラーなく終了する。

- [ ] **Step 3: コミット**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: バージョンを 0.1.3 から 0.1.4 に更新し httpx を main 依存へ移動する"
```

---

## Task 2: update_service.py — バージョンチェック機能（TDD）

**Files:**
- Create: `backend/services/update_service.py`
- Create: `tests/unit/test_update_service.py`

- [ ] **Step 1: テストファイルを作成して3つのテストを書く（失敗確認用）**

`tests/unit/test_update_service.py`:
```python
"""update_service のバージョンチェック機能の単体テスト。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import backend.services.update_service as svc


def _make_github_response(tag: str, assets: list[dict] | None = None) -> MagicMock:
    """GitHub API レスポンスのモックを生成する。"""
    mock = MagicMock()
    mock.json.return_value = {"tag_name": tag, "assets": assets or []}
    mock.raise_for_status = MagicMock()
    return mock


def test_check_update_新バージョンあり():
    # --- Arrange ---
    svc._cache["checked_at"] = None
    assets = [{"name": "GitLanes-0.2.0.dmg", "browser_download_url": "https://example.com/test.dmg"}]
    mock_resp = _make_github_response("v0.2.0", assets)

    # --- Act ---
    with patch("httpx.get", return_value=mock_resp):
        result = svc.check_update()

    # --- Assert ---
    assert result["available"] is True
    assert result["version"] == "0.2.0"
    assert result["download_url"] == "https://example.com/test.dmg"


def test_check_update_最新バージョン():
    # --- Arrange ---
    svc._cache["checked_at"] = None
    mock_resp = _make_github_response(f"v{svc._CURRENT_VERSION}")

    # --- Act ---
    with patch("httpx.get", return_value=mock_resp):
        result = svc.check_update()

    # --- Assert ---
    assert result["available"] is False


def test_check_update_キャッシュが効く():
    # --- Arrange ---
    svc._cache["checked_at"] = None
    mock_resp = _make_github_response("v0.2.0")

    # --- Act ---
    with patch("httpx.get", return_value=mock_resp) as mock_get:
        svc.check_update()
        svc.check_update()  # 2回目はキャッシュから返す

    # --- Assert ---
    assert mock_get.call_count == 1
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_update_service.py -v
```

期待: `ModuleNotFoundError: No module named 'backend.services.update_service'` で FAIL

- [ ] **Step 3: update_service.py の骨格とバージョンチェック機能を実装する**

`backend/services/update_service.py`:
```python
"""アプリ内自動アップデート処理。"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path

import httpx

GITHUB_API_URL = "https://api.github.com/repos/YTommy109/git-lanes/releases/latest"
_CACHE_TTL = 3600
_SCRIPT_PATH = Path("/tmp/git-lanes-updater.sh")

try:
    _CURRENT_VERSION = _pkg_version("git-lanes")
except PackageNotFoundError:
    _CURRENT_VERSION = "0.0.0"

_cache: dict = {"checked_at": None, "result": None}
_download_state: dict = {"percent": 0, "status": "idle", "dmg_path": None}


def _is_newer(remote: str, current: str) -> bool:
    """リモートバージョンが現在より新しいかを比較する。"""
    def to_tuple(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split("."))
    return to_tuple(remote) > to_tuple(current)


def _find_dmg_url(assets: list[dict]) -> str | None:
    """リリースアセットから DMG のダウンロード URL を取得する。"""
    for asset in assets:
        if asset.get("name", "").endswith(".dmg"):
            return asset.get("browser_download_url")
    return None


def check_update() -> dict:
    """GitHub Releases API で最新バージョンを確認する（1時間TTLキャッシュ）。

    Returns:
        available: 更新があれば True。version: 最新バージョン文字列。
        download_url: DMG のダウンロード URL（なければ None）。
    """
    now = time.monotonic()
    if _cache["checked_at"] and now - _cache["checked_at"] < _CACHE_TTL:
        return _cache["result"]
    try:
        resp = httpx.get(GITHUB_API_URL, timeout=5, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        tag = data["tag_name"].lstrip("v")
        result: dict = {
            "available": _is_newer(tag, _CURRENT_VERSION),
            "version": tag,
            "download_url": _find_dmg_url(data.get("assets", [])),
        }
    except Exception:
        result = {"available": False, "version": _CURRENT_VERSION, "download_url": None}
    _cache["checked_at"] = now
    _cache["result"] = result
    return result
```

（ダウンロード・インストール関数は次のタスクで追加する。現時点ではファイル末尾は `check_update` で終わる。）

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_update_service.py -v
```

期待:
```
PASSED tests/unit/test_update_service.py::test_check_update_新バージョンあり
PASSED tests/unit/test_update_service.py::test_check_update_最新バージョン
PASSED tests/unit/test_update_service.py::test_check_update_キャッシュが効く
```

- [ ] **Step 5: コミット**

```bash
git add backend/services/update_service.py tests/unit/test_update_service.py
git commit -m "feat: update_service のバージョンチェック機能を追加する"
```

---

## Task 3: update_service.py — ダウンロード機能（TDD）

**Files:**
- Modify: `backend/services/update_service.py`（ファイル末尾に追記）
- Modify: `tests/unit/test_update_service.py`（テスト追加）

- [ ] **Step 1: ダウンロードのテストを追加する**

`tests/unit/test_update_service.py` の末尾に追加:
```python
def test_download_update_進捗更新(tmp_path):
    # --- Arrange ---
    svc._download_state.update({"percent": 0, "status": "idle", "dmg_path": None})
    chunk_data = [b"a" * 50, b"b" * 50]
    dmg_dest = tmp_path / "test.dmg"

    class FakeResponse:
        headers = {"content-length": "100"}

        def raise_for_status(self) -> None:
            pass

        def iter_bytes(self, chunk_size: int | None = None):
            return iter(chunk_data)

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    # --- Act ---
    with patch("httpx.stream", return_value=FakeResponse()):
        svc._do_download("https://example.com/test.dmg", dest=dmg_dest)

    # --- Assert ---
    assert svc._download_state["status"] == "done"
    assert svc._download_state["percent"] == 100
    assert svc._download_state["dmg_path"] == str(dmg_dest)
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_update_service.py::test_download_update_進捗更新 -v
```

期待: `AttributeError: module ... has no attribute '_do_download'` で FAIL

- [ ] **Step 3: ダウンロード機能を update_service.py に追記する**

`check_update` 関数の後ろに以下を追記:
```python

def get_download_state() -> dict:
    """ダウンロード状態のコピーを返す。"""
    return dict(_download_state)


def _do_download(url: str, dest: Path | None = None) -> None:
    """実際のダウンロード処理（バックグラウンドスレッドで実行）。

    Args:
        url: DMG のダウンロード URL。
        dest: 保存先パス。None のとき ~/Downloads/GitLanes-update.dmg に保存する。
    """
    _download_state.update({"percent": 0, "status": "downloading", "dmg_path": None})
    dmg_path = dest or Path.home() / "Downloads" / "GitLanes-update.dmg"
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=300) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with dmg_path.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        _download_state["percent"] = int(downloaded / total * 100)
        _download_state["status"] = "done"
        _download_state["dmg_path"] = str(dmg_path)
    except Exception:
        _download_state["status"] = "error"


def download_update(url: str) -> None:
    """ダウンロードをバックグラウンドスレッドで開始する。

    Args:
        url: DMG のダウンロード URL。
    """
    if _download_state["status"] == "downloading":
        return
    threading.Thread(target=_do_download, args=(url,), daemon=True).start()
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_update_service.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add backend/services/update_service.py tests/unit/test_update_service.py
git commit -m "feat: update_service のダウンロード機能を追加する"
```

---

## Task 4: update_service.py — インストール補助関数（TDD）

**Files:**
- Modify: `backend/services/update_service.py`（ファイル末尾に追記）
- Modify: `tests/unit/test_update_service.py`（テスト追加）

- [ ] **Step 1: インストール補助関数のテストを追加する**

`tests/unit/test_update_service.py` の末尾に追加:
```python
def test_get_app_path_frozen環境():
    # --- Arrange ---
    fake_exe = "/Applications/Git Lanes.app/Contents/MacOS/Git Lanes"

    # --- Act ---
    with patch.object(sys, "frozen", True, create=True):
        with patch.object(sys, "executable", fake_exe):
            result = svc._get_app_path()

    # --- Assert ---
    assert result == Path("/Applications/Git Lanes.app")


def test_get_app_path_開発環境():
    # --- Arrange / Act ---
    with patch.object(sys, "frozen", False, create=True):
        result = svc._get_app_path()

    # --- Assert ---
    assert result is None


def test_write_updater_script_内容検証(tmp_path):
    # --- Arrange ---
    app_path = Path("/Applications/Git Lanes.app")
    mount_point = Path("/Volumes/Git Lanes")
    new_app_src = Path("/Volumes/Git Lanes/Git Lanes.app")
    script_path = tmp_path / "git-lanes-updater.sh"

    # --- Act ---
    with patch.object(svc, "_SCRIPT_PATH", script_path):
        result = svc._write_updater_script(app_path, mount_point, new_app_src)

    # --- Assert ---
    content = result.read_text()
    assert "hdiutil detach" in content
    assert f'open "{app_path}"' in content
    assert str(app_path) in content
```

`tests/unit/test_update_service.py` の冒頭の import に `sys` を追加:
```python
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_update_service.py::test_get_app_path_frozen環境 tests/unit/test_update_service.py::test_get_app_path_開発環境 tests/unit/test_update_service.py::test_write_updater_script_内容検証 -v
```

期待: `AttributeError: module ... has no attribute '_get_app_path'` で FAIL

- [ ] **Step 3: インストール補助関数を update_service.py に追記する**

`download_update` 関数の後ろに以下を追記:
```python

def _get_app_path() -> Path | None:
    """PyInstaller 環境での .app バンドルパスを返す。

    Returns:
        .app バンドルの Path。開発環境（sys.frozen が偽）なら None。
    """
    if not getattr(sys, "frozen", False):
        return None
    # sys.executable = /Applications/Git Lanes.app/Contents/MacOS/Git Lanes
    return Path(sys.executable).parent.parent.parent


def _write_updater_script(app_path: Path, mount_point: Path, new_app_src: Path) -> Path:
    """インストール用シェルスクリプトを /tmp に書き出す。

    Args:
        app_path: 現在の .app パス（削除対象）。
        mount_point: DMG のマウントポイント（アンマウント対象）。
        new_app_src: DMG 内の新しい .app パス（コピー元）。

    Returns:
        書き出したスクリプトの Path。
    """
    script = (
        "#!/bin/bash\n"
        "sleep 3\n"
        f'rm -rf "{app_path}"\n'
        f'cp -R "{new_app_src}" "{app_path.parent}/"\n'
        f'hdiutil detach "{mount_point}" -quiet\n'
        f'open "{app_path}"\n'
    )
    _SCRIPT_PATH.write_text(script)
    _SCRIPT_PATH.chmod(0o755)
    return _SCRIPT_PATH
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_update_service.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add backend/services/update_service.py tests/unit/test_update_service.py
git commit -m "feat: update_service のインストール補助関数を追加する"
```

---

## Task 5: update_service.py — install_update 関数（TDD）

**Files:**
- Modify: `backend/services/update_service.py`（ファイル末尾に追記）
- Modify: `tests/unit/test_update_service.py`（テスト追加）

- [ ] **Step 1: install_update のテストを追加する**

`tests/unit/test_update_service.py` の末尾に追加:
```python
def test_install_update_開発環境ではスキップ(tmp_path):
    # --- Arrange ---
    # dmg_path をセットして "done" 状態にする
    svc._download_state.update(
        {"percent": 100, "status": "done", "dmg_path": str(tmp_path / "test.dmg")}
    )

    # --- Act ---
    # _get_app_path が None を返す（開発環境）ので sys.exit は呼ばれない
    with patch.object(sys, "frozen", False, create=True):
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "/dev/disk4\t\t\n/dev/disk4s1\tApple_HFS\t/Volumes/Test\n"
            mock_run.return_value = mock_result
            (tmp_path / "Test.app").mkdir()

            with patch.object(Path, "glob", return_value=[tmp_path / "Test.app"]):
                svc.install_update()  # sys.exit(0) は呼ばれないはず

    # --- Assert ---
    # 開発環境では何もせずに return するので例外なく完了する
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_update_service.py::test_install_update_開発環境ではスキップ -v
```

期待: `AttributeError: module ... has no attribute 'install_update'` で FAIL

- [ ] **Step 3: install_update を update_service.py に追記する**

`_write_updater_script` の後ろに以下を追記:
```python

def install_update() -> None:
    """DMG をマウントして .app を差し替え、再起動スクリプトを実行する。

    開発環境（sys.frozen が偽）では何もせず return する。
    ダウンロードが完了していない場合も何もせず return する。
    """
    dmg_path = _download_state.get("dmg_path")
    if not dmg_path:
        return
    result = subprocess.run(
        ["hdiutil", "attach", dmg_path, "-nobrowse"],
        capture_output=True,
        text=True,
        check=True,
    )
    last_line = result.stdout.strip().split("\n")[-1]
    mount_point = Path(last_line.split("\t")[-1].strip())
    apps = list(mount_point.glob("*.app"))
    if not apps:
        return
    app_path = _get_app_path()
    if app_path is None:
        return
    script_path = _write_updater_script(app_path, mount_point, apps[0])
    subprocess.Popen(["bash", str(script_path)])
    sys.exit(0)
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_update_service.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: Ruff でコードを検査する**

```bash
uv run ruff check backend/services/update_service.py
uv run ruff format --check backend/services/update_service.py
```

期待: エラーなし。フォーマット違反があれば `uv run ruff format backend/services/update_service.py` で修正する。

- [ ] **Step 6: コミット**

```bash
git add backend/services/update_service.py tests/unit/test_update_service.py
git commit -m "feat: update_service の install_update 関数を追加する"
```

---

## Task 6: routers/update.py の実装と main.py への追加

**Files:**
- Create: `backend/routers/update.py`
- Modify: `backend/main.py`

- [ ] **Step 1: backend/routers/update.py を作成する**

```python
# backend/routers/update.py
"""アップデート確認・ダウンロード・インストールの API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.services import update_service

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
router = APIRouter(prefix="/api/update", tags=["update"])


@router.get("/check", response_class=HTMLResponse)
def check_update(request: Request) -> HTMLResponse:
    """更新確認。更新がなければ空レスポンスを返す。"""
    result = update_service.check_update()
    if not result["available"]:
        return HTMLResponse(content="")
    return templates.TemplateResponse(
        request,
        "partials/update_banner.html",
        {"version": result["version"], "download_url": result["download_url"]},
    )


@router.post("/download", response_class=HTMLResponse)
def start_download(request: Request) -> HTMLResponse:
    """ダウンロードを開始し、進捗 UI を返す。"""
    result = update_service.check_update()
    if result["download_url"]:
        update_service.download_update(result["download_url"])
    state = update_service.get_download_state()
    return templates.TemplateResponse(
        request,
        "partials/update_progress.html",
        {"percent": state["percent"], "status": state["status"]},
    )


@router.get("/progress", response_class=HTMLResponse)
def get_progress(request: Request) -> HTMLResponse:
    """ダウンロード進捗 HTML を返す（1秒ポーリング用）。"""
    state = update_service.get_download_state()
    return templates.TemplateResponse(
        request,
        "partials/update_progress.html",
        {"percent": state["percent"], "status": state["status"]},
    )


@router.post("/install")
def install_update() -> None:
    """インストールして再起動する。"""
    update_service.install_update()
```

- [ ] **Step 2: backend/main.py に update ルーターを追加する**

`backend/main.py` の `from backend.routers import api, html` の行を以下に変更:
```python
from backend.routers import api, html, update
```

`app.include_router(api.router)` の後に以下を追加:
```python
app.include_router(update.router)
```

変更後の `backend/main.py` 全体:
```python
# backend/main.py
"""FastAPI アプリケーションのエントリポイント。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.db import create_db_and_tables
from backend.routers import api, html, update

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
app.include_router(update.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """サーバーの稼働確認用エンドポイント。"""
    return {"status": "ok"}
```

- [ ] **Step 3: サーバーが起動することを確認する**

```bash
uv run task dev
```

別ターミナルで:
```bash
curl http://localhost:8000/api/update/check
curl http://localhost:8000/api/update/progress
```

期待: 200 OK が返る（check は空レスポンス、progress は HTML 断片）

Ctrl+C でサーバーを停止する。

- [ ] **Step 4: Ruff でコードを検査する**

```bash
uv run ruff check backend/routers/update.py backend/main.py
uv run ruff format --check backend/routers/update.py backend/main.py
```

期待: エラーなし。

- [ ] **Step 5: コミット**

```bash
git add backend/routers/update.py backend/main.py
git commit -m "feat: アップデート API エンドポイントを追加する"
```

---

## Task 7: テンプレートの実装

**Files:**
- Modify: `backend/templates/base.html`
- Create: `backend/templates/partials/update_banner.html`
- Create: `backend/templates/partials/update_progress.html`

- [ ] **Step 1: update_banner.html を作成する**

`backend/templates/partials/update_banner.html`:
```html
<div id="update-banner"
     style="padding: 0.5rem 0.75rem; font-size: 0.8rem; border-top: 1px solid var(--divider); background: var(--base-2)">
  <p style="margin: 0 0 0.4rem; font-weight: bold">v{{ version }} があります</p>
  <button
    hx-post="/api/update/download"
    hx-target="#update-banner"
    hx-swap="outerHTML"
    style="font-size: 0.75rem; width: 100%">
    ダウンロード
  </button>
</div>
```

- [ ] **Step 2: update_progress.html を作成する**

`backend/templates/partials/update_progress.html`:
```html
<div id="update-banner"
     style="padding: 0.5rem 0.75rem; font-size: 0.8rem; border-top: 1px solid var(--divider); background: var(--base-2)"
     {% if status == "downloading" %}
     hx-get="/api/update/progress"
     hx-trigger="every 1s"
     hx-swap="outerHTML"
     {% endif %}>
  {% if status == "downloading" %}
    <p style="margin: 0 0 0.3rem">ダウンロード中...</p>
    <progress value="{{ percent }}" max="100" style="width: 100%"></progress>
    <p style="margin: 0.2rem 0 0; font-size: 0.7rem">{{ percent }}%</p>
  {% elif status == "done" %}
    <p style="margin: 0 0 0.4rem">ダウンロード完了</p>
    <button
      hx-post="/api/update/install"
      style="font-size: 0.75rem; width: 100%">
      インストールして再起動
    </button>
  {% elif status == "error" %}
    <p style="margin: 0; color: var(--color-caution)">ダウンロードに失敗しました</p>
  {% endif %}
</div>
```

- [ ] **Step 3: base.html にバナー挿入スロットを追加する**

`backend/templates/base.html` の `</nav>` の直前（`<form>` タグの閉じタグ `</form>` の後）に以下を追加:
```html
    <div id="update-banner"
         hx-get="/api/update/check"
         hx-trigger="load"
         hx-swap="outerHTML">
    </div>
```

変更後の nav 末尾部分（`</nav>` 直前）:
```html
    <form method="post" action="/api/repos" class="l--stack -g:8"
          _="on submit toggle @disabled on <button/>">
      <label class="l--stack -g:4" style="font-size: 0.8rem">
        パスを追加
        <input name="path" type="text" required autocomplete="off"
               placeholder="/path/to/repo"
               style="width: 100%; padding: 0.3rem 0.4rem; font-size: 0.8rem"/>
      </label>
      <button type="submit" style="font-size: 0.8rem">追加</button>
    </form>
    <div id="update-banner"
         hx-get="/api/update/check"
         hx-trigger="load"
         hx-swap="outerHTML">
    </div>
  </nav>
```

- [ ] **Step 4: サーバーを起動してブラウザで確認する**

```bash
uv run task dev
```

ブラウザで `http://localhost:8000/` を開く。

確認事項:
- ページロード時に `/api/update/check` が呼ばれる（DevTools の Network タブで確認）
- 更新なし → バナーが表示されない
- `uv run python -c "import backend.services.update_service as s; s._cache['checked_at'] = None; s._cache['result'] = {'available': True, 'version': '99.0.0', 'download_url': 'https://example.com/test.dmg'}"` を実行後にリロードするとバナーが表示される（開発確認用）

- [ ] **Step 5: 全テストが通ることを確認する**

```bash
uv run task test
```

期待: 全テスト PASS

- [ ] **Step 6: コミット**

```bash
git add backend/templates/base.html backend/templates/partials/update_banner.html backend/templates/partials/update_progress.html
git commit -m "feat: アップデート通知バナーと進捗 UI テンプレートを追加する"
```

---

## 完了チェックリスト

- [ ] `pyproject.toml` のバージョンが `0.1.4`、httpx が main 依存にある
- [ ] `uv run task test` が全 PASS
- [ ] `uv run task lint` がエラーなし
- [ ] `uv run task typecheck` がエラーなし
- [ ] ページロード時に `/api/update/check` が呼ばれている（DevTools で確認）
