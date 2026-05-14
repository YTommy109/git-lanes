# Check for Updates メニュー Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mac メニューバーに「Check for Updates...」を追加し、最新ならシンプルメッセージ、更新ありならダウンロード→インストールまで完結するサブウィンドウを表示する。

**Architecture:** pywebview の `webview.Menu` / `webview.MenuAction` でネイティブメニューを登録し、クリック時に `webview.create_window()` で小さなサブウィンドウ（400×260px）を開く。ウィンドウは `/api/update/dialog`（新 FastAPI エンドポイント）をロードし、htmx で既存のダウンロード・インストールフローを再利用する。キャッシュは `invalidate_cache()` でクリアして即時チェックを強制する。

**Tech Stack:** Python 3.12 / FastAPI / pywebview 6.x / Jinja2 / htmx 2.x / pytest

---

## ファイル構成

| ファイル | 変更種別 | 責務 |
|---|---|---|
| `backend/services/update_service.py` | 修正 | `invalidate_cache()` を追加 |
| `backend/routers/update.py` | 修正 | `GET /api/update/dialog` エンドポイントを追加 |
| `backend/templates/update_dialog.html` | 新規 | スタンドアロン更新ダイアログ HTML |
| `backend/app.py` | 修正 | `_update_win` 管理・`_open_update_dialog`・メニュー登録 |
| `tests/unit/test_update_service.py` | 修正 | `invalidate_cache` テスト追加 |
| `tests/unit/test_app.py` | 修正 | `/api/update/dialog` テスト追加 |

---

## Task 1: update_service に invalidate_cache() を追加する

**Files:**
- Modify: `backend/services/update_service.py`
- Test: `tests/unit/test_update_service.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unit/test_update_service.py` の末尾に追加する:

```python
def test_invalidate_cache_はキャッシュをクリアする():
    # --- Arrange ---
    import time
    svc._cache["checked_at"] = time.monotonic()
    svc._cache["result"] = {"available": False, "version": "0.1.0", "download_url": None}

    # --- Act ---
    svc.invalidate_cache()

    # --- Assert ---
    assert svc._cache["checked_at"] is None
    assert svc._cache["result"] is None
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_update_service.py::test_invalidate_cache_はキャッシュをクリアする -v
```

期待: `FAILED` — `AttributeError: module has no attribute 'invalidate_cache'`

- [ ] **Step 3: invalidate_cache() を実装する**

`backend/services/update_service.py` の `download_update` 関数の直前（`def download_update` の 1 行上）に追加する:

```python
def invalidate_cache() -> None:
    """更新確認キャッシュを無効化する（次回 check_update で強制再取得）。"""
    _cache["checked_at"] = None
    _cache["result"] = None
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_update_service.py -v
```

期待: 全テスト PASSED

- [ ] **Step 5: コミットする**

```bash
git add backend/services/update_service.py tests/unit/test_update_service.py
git commit -m "feat: update_service に invalidate_cache を追加する"
```

---

## Task 2: /api/update/dialog エンドポイントとテンプレートを追加する

**Files:**
- Modify: `backend/routers/update.py`
- Create: `backend/templates/update_dialog.html`
- Test: `tests/unit/test_app.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unit/test_app.py` のインポート部分はすでに `from unittest.mock import MagicMock, patch` と `from fastapi.testclient import TestClient` と `from backend.main import app` がある。末尾に以下を追加する:

```python
def test_update_dialog_最新状態のとき200を返す():
    # --- Arrange ---
    import backend.services.update_service as svc

    svc._cache["checked_at"] = None
    client = TestClient(app)

    # --- Act ---
    with patch("backend.services.update_service.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": f"v{svc._CURRENT_VERSION}",
            "assets": [],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        response = client.get("/api/update/dialog")

    # --- Assert ---
    assert response.status_code == 200
    assert "最新バージョンです" in response.text


def test_update_dialog_更新ありのとき200を返す():
    # --- Arrange ---
    import backend.services.update_service as svc

    svc._cache["checked_at"] = None
    client = TestClient(app)

    # --- Act ---
    with patch("backend.services.update_service.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": "v999.0.0",
            "assets": [
                {
                    "name": "GitLanes-999.0.0.dmg",
                    "browser_download_url": "https://example.com/test.dmg",
                }
            ],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        response = client.get("/api/update/dialog")

    # --- Assert ---
    assert response.status_code == 200
    assert "999.0.0" in response.text
    assert "ダウンロード" in response.text
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_app.py::test_update_dialog_最新状態のとき200を返す tests/unit/test_app.py::test_update_dialog_更新ありのとき200を返す -v
```

期待: `FAILED` — `404 Not Found`

- [ ] **Step 3: エンドポイントを追加する**

`backend/routers/update.py` の既存インポート行（`from backend.services import update_service` の下）に追加する:

```python
from backend.version import __version__ as _CURRENT_VERSION
```

既存の `router = APIRouter(prefix="/api/update", tags=["update"])` の下、`@router.get("/check", ...)` の直前に新エンドポイントを追加する:

```python
@router.get("/dialog", response_class=HTMLResponse)
def update_dialog(request: Request) -> HTMLResponse:
    """更新確認ダイアログ用ページを返す。"""
    result = update_service.check_update()
    return templates.TemplateResponse(
        request,
        "update_dialog.html",
        {
            "available": result["available"],
            "latest_version": result["version"],
            "current_version": _CURRENT_VERSION,
            "download_url": result["download_url"],
        },
    )
```

既存の `router = APIRouter(prefix="/api/update", ...)` はそのまま維持する。このエンドポイントは prefix により `/api/update/dialog` になる。

- [ ] **Step 4: update_dialog.html を作成する**

`backend/templates/update_dialog.html` を新規作成する（base.html を継承しない）:

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8"/>
  <title>アップデート確認</title>
  <link href="https://cdn.jsdelivr.net/npm/lism-css@0.16.0/dist/css/main.css" rel="stylesheet"/>
  <link rel="stylesheet" href="/static/css/style.css"/>
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <script src="https://unpkg.com/hyperscript.org@0.9.14"></script>
</head>
<body>
<main class="l--stack -p:40" style="max-width: 360px; margin: 2rem auto">
  {% if not available %}
  <p style="font-size: 1.5rem; margin: 0">✓</p>
  <h2 style="margin: 0.5rem 0 0">最新バージョンです</h2>
  <p class="-c:text-2" style="margin: 0.5rem 0 0">
    Git Lanes v{{ current_version }} は最新バージョンです。
  </p>
  {% else %}
  <div id="update-banner" class="l--stack -g:16">
    <h2 style="margin: 0">v{{ latest_version }} が利用可能です</h2>
    <dl class="l--stack -g:4" style="font-size: 0.9rem; margin: 0">
      <div class="l--flex -gap:8">
        <dt class="-c:text-2" style="min-width: 3rem">現在</dt>
        <dd style="margin: 0">v{{ current_version }}</dd>
      </div>
      <div class="l--flex -gap:8">
        <dt class="-c:text-2" style="min-width: 3rem">最新</dt>
        <dd style="margin: 0">v{{ latest_version }}</dd>
      </div>
    </dl>
    {% if download_url %}
    <button
      hx-post="/api/update/download"
      hx-target="#update-banner"
      hx-swap="outerHTML"
      style="font-size: 0.9rem">
      ダウンロード
    </button>
    {% else %}
    <p class="-c:text-2" style="font-size: 0.85rem; margin: 0">
      <a href="https://github.com/YTommy109/git-lanes/releases/latest" target="_blank">
        GitHub リリースページ
      </a>からダウンロードしてください。
    </p>
    {% endif %}
  </div>
  {% endif %}
</main>
</body>
</html>
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_app.py -v
```

期待: 全テスト PASSED

- [ ] **Step 6: コミットする**

```bash
git add backend/routers/update.py backend/templates/update_dialog.html tests/unit/test_app.py
git commit -m "feat: /api/update/dialog エンドポイントとテンプレートを追加する"
```

---

## Task 3: Mac メニューに「Check for Updates...」を登録する

pywebview はテストクライアントで単体テストできないため、実装後に `uv run task app` で手動確認する。

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: _update_win グローバルと _open_update_dialog 関数を追加する**

`backend/app.py` の既存インポートに追加する（`from backend.state_store import WindowState` の下）:

```python
from backend.services import update_service
```

`_save_timer: threading.Timer | None = None` と `_timer_lock = threading.Lock()` の直後に追加する:

```python
_update_win: Window | None = None
```

`_schedule_save` 関数の直前に追加する:

```python
def _open_update_dialog(port: int) -> None:
    """更新確認ダイアログを開く。すでに開いていれば何もしない。

    Args:
        port: FastAPI が Listen しているポート番号。
    """
    global _update_win
    if _update_win is not None:
        return
    update_service.invalidate_cache()
    url = f"http://{HOST}:{port}/api/update/dialog"
    win = webview.create_window(
        title="アップデート確認",
        url=url,
        width=400,
        height=260,
        resizable=False,
    )

    def _on_closed() -> None:
        global _update_win
        _update_win = None

    win.events.closed += _on_closed
    _update_win = win
```

- [ ] **Step 2: main() にメニューを登録する**

`backend/app.py` の `main()` 関数内、`port = _find_free_port()` の直後に以下を追加する:

```python
    menu = [
        webview.Menu(
            "Git Lanes",
            [
                webview.MenuAction(
                    "Check for Updates...",
                    lambda: _open_update_dialog(port),
                ),
            ],
        )
    ]
```

`webview.start()` の呼び出し行を以下に変更する:

```python
    webview.start(menu=menu)
```

- [ ] **Step 3: 手動でアプリを起動して動作確認する**

```bash
uv run task app
```

確認項目:
1. メニューバーに「Git Lanes」メニューが表示される
2. 「Check for Updates...」をクリックすると 400×260px のウィンドウが開く
3. 最新バージョンのとき「✓ 最新バージョンです」が表示される
4. 2 枚目が開かない（ダイアログが開いている状態で再クリックしても無視される）
5. × で閉じた後に再クリックすると新しいウィンドウが開く

更新ありケースの確認（環境変数でモック）:

```bash
GL_MOCK_DMG=/tmp/test.dmg uv run task app
```

確認項目:
6. 「v999.0.0 が利用可能です」が表示される
7. 「ダウンロード」ボタンをクリックすると進捗 UI に切り替わる

- [ ] **Step 4: 全テストを実行して既存テストが壊れていないか確認する**

```bash
uv run task test
```

期待: 全テスト PASSED、カバレッジ 85% 以上

- [ ] **Step 5: コミットする**

```bash
git add backend/app.py
git commit -m "feat: Mac メニューに Check for Updates を追加する"
```
