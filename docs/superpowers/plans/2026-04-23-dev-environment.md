# 開発環境セットアップ 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** git-lanes プロジェクトの開発環境を整備し、`uv sync` から E2E テストまで一気通貫で動作する状態にする。

**Architecture:** Python/FastAPI バックエンドを `backend/` に配置し、pytest 単体テストと Python Playwright E2E テストを `tests/` に配置する。依存管理は uv、タスク実行は taskipy、Lint/Format は ruff、型チェックは ty、DB マイグレーションは Atlas 宣言型で管理する。

**Tech Stack:** Python 3.12+, FastAPI, uvicorn, pygit2, watchdog, jinja2, pytest, pytest-playwright, playwright, taskipy, ruff, ty, pre-commit, Atlas（外部バイナリ）

---

## ファイルマップ

| ファイル | 役割 |
|---------|------|
| `pyproject.toml` | Python 依存・taskipy・ruff・ty・pytest 設定 |
| `.pre-commit-config.yaml` | コミット前ゲート（ruff + ty + pre-commit-hooks） |
| `schema.hcl` | Atlas DB スキーマ定義 |
| `backend/__init__.py` | Python パッケージマーカー（空） |
| `backend/main.py` | FastAPI アプリエントリポイント |
| `backend/routers/.gitkeep` | ルーター格納先（後日追加） |
| `backend/services/.gitkeep` | サービス格納先（後日追加） |
| `backend/templates/.gitkeep` | Jinja2 テンプレート格納先（後日追加） |
| `tests/__init__.py` | テストパッケージマーカー（空） |
| `tests/unit/__init__.py` | 単体テストパッケージマーカー（空） |
| `tests/unit/test_app.py` | FastAPI ヘルスチェックの単体テスト |
| `tests/e2e/__init__.py` | E2E テストパッケージマーカー（空） |
| `tests/e2e/conftest.py` | Playwright 用サーバー起動 fixture |
| `tests/e2e/test_smoke.py` | E2E スモークテスト |
| `README.md` | セットアップ手順・開発コマンド一覧 |
| `LICENSE` | MIT License |
| `docs/technology.md` | ty・Python Playwright の追記 |

---

### Task 1: pyproject.toml を作成する

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: pyproject.toml を作成する**

```toml
[project]
name = "git-lanes"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "pygit2",
    "watchdog",
    "jinja2",
]

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
]

[tool.taskipy.tasks]
dev         = "uvicorn backend.main:app --reload --port 8000"
test        = "pytest tests/unit -v"
"test:e2e"  = "pytest tests/e2e -v"
lint        = "ruff check ."
format      = "ruff format ."
typecheck   = "ty check"
migrate     = "atlas schema apply --url 'sqlite://${DB_PATH:-dev.db}' --to 'file://schema.hcl' --dev-url 'sqlite://dev?mode=memory'"
build       = "echo 'TODO: Electron build'"

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "C901"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.pytest.ini_options]
testpaths = ["tests/unit"]

[tool.ty.environment]
python-version = "3.12"
```

- [ ] **Step 2: コミット**

```bash
git add pyproject.toml
git commit -m "chore: pyproject.toml を追加する"
```

---

### Task 2: .pre-commit-config.yaml を作成する

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: .pre-commit-config.yaml を作成する**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: ty
        name: ty
        entry: uv run ty check
        language: system
        types: [python]
        pass_filenames: false

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
```

- [ ] **Step 2: コミット**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: .pre-commit-config.yaml を追加する"
```

---

### Task 3: backend スケルトンと単体テストを作成する

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/main.py`
- Create: `backend/routers/.gitkeep`
- Create: `backend/services/.gitkeep`
- Create: `backend/templates/.gitkeep`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_app.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unit/test_app.py`:

```python
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_ヘルスチェックが200を返す():
    # --- Arrange ---
    # TestClient は ASGI アプリを受け取り同期的に動作する

    # --- Act ---
    response = client.get("/health")

    # --- Assert ---
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

`tests/__init__.py`（空）、`tests/unit/__init__.py`（空）も作成する。

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_app.py -v
```

期待結果: `ModuleNotFoundError: No module named 'backend'`

- [ ] **Step 3: backend スケルトンを実装する**

`backend/__init__.py`（空）

`backend/main.py`:

```python
"""FastAPI アプリケーションのエントリポイント。"""
from fastapi import FastAPI

app = FastAPI(title="Git Lanes")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """サーバーの稼働確認用エンドポイント。"""
    return {"status": "ok"}
```

`backend/routers/.gitkeep`、`backend/services/.gitkeep`、`backend/templates/.gitkeep`（各空ファイル）

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_app.py -v
```

期待結果:
```
tests/unit/test_app.py::test_ヘルスチェックが200を返す PASSED
1 passed in 0.xx s
```

- [ ] **Step 5: コミット**

```bash
git add backend/ tests/unit/ tests/__init__.py
git commit -m "feat: backend スケルトンと単体テストを追加する"
```

---

### Task 4: E2E テスト環境を作成する

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`
- Create: `tests/e2e/test_smoke.py`

- [ ] **Step 1: E2E スモークテストを書く**

`tests/e2e/test_smoke.py`:

```python
from playwright.sync_api import Page


def test_ヘルスチェックエンドポイントが応答する(page: Page, base_url: str):
    # Given: アプリが起動している（conftest の _server fixture が保証）
    # When: ヘルスチェックエンドポイントにリクエストする
    response = page.request.get(f"{base_url}/health")

    # Then: 200 と {"status": "ok"} が返る
    assert response.status == 200
    assert response.json()["status"] == "ok"
```

`tests/e2e/__init__.py`（空）

- [ ] **Step 2: conftest.py でサーバー起動 fixture を作成する**

`tests/e2e/conftest.py`:

```python
"""E2E テスト用 fixture。FastAPI サーバーをサブプロセスで起動する。"""
import subprocess
import time
import urllib.error
import urllib.request

import pytest


@pytest.fixture(scope="session")
def _server():
    """テストセッション中 FastAPI サーバーをポート 8001 で起動する。"""
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "backend.main:app", "--port", "8001"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # サーバーが応答するまで最大 10 秒待機する
    for _ in range(20):
        try:
            urllib.request.urlopen("http://localhost:8001/health", timeout=1)
            break
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    yield
    proc.terminate()
    proc.wait()


@pytest.fixture
def base_url(_server: None) -> str:
    return "http://localhost:8001"
```

- [ ] **Step 3: E2E テストが通ることを確認する**

```bash
uv run pytest tests/e2e/test_smoke.py -v
```

期待結果:
```
tests/e2e/test_smoke.py::test_ヘルスチェックエンドポイントが応答する PASSED
1 passed in x.xx s
```

- [ ] **Step 4: コミット**

```bash
git add tests/e2e/
git commit -m "test: E2E スモークテストを追加する"
```

---

### Task 5: schema.hcl を作成する

**Files:**
- Create: `schema.hcl`

- [ ] **Step 1: schema.hcl を作成する**

```hcl
# Git Lanes DB スキーマ定義（Atlas 宣言型マイグレーション）
# 適用: atlas schema apply --url 'sqlite://dev.db' --to 'file://schema.hcl' --dev-url 'sqlite://dev?mode=memory'

schema "main" {}

table "repositories" {
  schema = schema.main

  column "id" {
    type = text
    null = false
  }

  column "path" {
    type = text
    null = false
  }

  column "name" {
    type = text
    null = false
  }

  primary_key {
    columns = [column.id]
  }
}
```

- [ ] **Step 2: コミット**

```bash
git add schema.hcl
git commit -m "chore: Atlas スキーマ定義を追加する"
```

---

### Task 6: README.md を作成する

**Files:**
- Create: `README.md`

- [ ] **Step 1: README.md を作成する**

````markdown
# Git Lanes

Git リポジトリのブランチ構造を可視化する Mac デスクトップアプリ。

## 技術スタック

| 役割 | 技術 |
|------|------|
| バックエンド | Python 3.12+ / FastAPI |
| Git 操作 | pygit2 |
| FS 監視 | watchdog |
| DB | SQLite（Atlas 宣言型マイグレーション） |
| SVG / HTML 生成 | Jinja2 |
| フロントエンド | htmx + hyperscript |
| E2E テスト | Playwright（Python） |
| デスクトップシェル | Electron（予定） |

## 必要環境

| ツール | インストール方法 |
|-------|----------------|
| uv | `brew install uv` |
| atlas | `brew install ariga/tap/atlas` |

## セットアップ

```bash
uv sync
uv run playwright install chromium
pre-commit install
```

## 開発コマンド

```bash
uv run task dev        # FastAPI 開発サーバー起動（http://localhost:8000）
uv run task test       # 単体テスト（pytest）
uv run task test:e2e   # E2E テスト（Playwright）
uv run task lint       # Lint（ruff）
uv run task format     # フォーマット（ruff）
uv run task typecheck  # 型チェック（ty）
uv run task migrate    # DB マイグレーション（Atlas）
```

## ライセンス

MIT
````

- [ ] **Step 2: コミット**

```bash
git add README.md
git commit -m "docs: README.md を追加する"
```

---

### Task 7: LICENSE ファイルを作成する

**Files:**
- Create: `LICENSE`

- [ ] **Step 1: LICENSE ファイルを作成する**

```
MIT License

Copyright (c) 2026 Tommy109

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: コミット**

```bash
git add LICENSE
git commit -m "docs: MIT License を追加する"
```

---

### Task 8: docs/technology.md を更新する

**Files:**
- Modify: `docs/technology.md`

- [ ] **Step 1: 採用ツール一覧表に ty を追加する**

`docs/technology.md` の「採用ツール一覧」表（92〜95 行付近）を以下に更新する:

```markdown
| ツール | 対象言語 | 用途 |
|--------|----------|------|
| [Ruff](https://github.com/astral-sh/ruff) | Python | リント・フォーマット（Rust 実装） |
| [ty](https://github.com/astral-sh/ty) | Python | 型チェック（Rust 実装・Astral 製） |
| [rustfmt](https://github.com/rust-lang/rustfmt) | Rust（将来採用時） | フォーマット |
```

- [ ] **Step 2: Playwright の説明を Python 版に更新する**

`docs/technology.md` の Playwright セクション（80〜83 行付近）を以下に更新する:

```markdown
### Playwright

- Python バインディング（`pytest-playwright`）を使用し、FastAPI の Web UI をブラウザ経由でテストする
- Electron 対応は後日追加する（`_electron.launch()` を使用予定）
- ボタンの `disabled` 属性や aria 状態の検証が容易で、E2E 重点項目（操作制御）と相性が良い
- `pytest-playwright` の `page` fixture により htmx の非同期 DOM 更新を自動待機できる
```

- [ ] **Step 3: コミット**

```bash
git add docs/technology.md
git commit -m "docs: ty と Python Playwright を技術スタックに反映する"
```

---

### Task 9: 依存関係のインストールと動作確認

**Files:** （なし — インストールのみ）

- [ ] **Step 1: uv sync を実行する**

```bash
uv sync
```

期待結果: `Resolved X packages` のような出力で終了コード 0。`uv.lock` が生成される。

- [ ] **Step 2: Playwright ブラウザをインストールする**

```bash
uv run playwright install chromium
```

期待結果: `Chromium X.X.X` のダウンロード・インストール完了メッセージ

- [ ] **Step 3: pre-commit フックをインストールする**

```bash
pre-commit install
```

期待結果: `pre-commit installed at .git/hooks/pre-commit`

- [ ] **Step 4: 全タスクの動作確認**

```bash
uv run task lint
uv run task typecheck
uv run task test
uv run task test:e2e
```

各コマンドが終了コード 0 で完了することを確認する。

- [ ] **Step 5: uv.lock をコミットする**

```bash
git add uv.lock
git commit -m "chore: uv.lock を追加する"
```
