# 開発環境セットアップ 設計書

**作成日**: 2026-04-23  
**対象**: git-lanes プロジェクトの開発環境初期構築

---

## 概要

Python / Electron ハイブリッドアプリの開発環境を整備する。  
`uv sync` 1 コマンドで依存関係を揃え、`uv run task <name>` で各種タスクを実行できる状態にする。  
E2E テストは Python Playwright でブラウザのみを対象とし、Electron 対応は後日追加する。

---

## ディレクトリ構造

```
git-lanes/
├── backend/               # FastAPI アプリ本体
│   ├── __init__.py
│   ├── main.py            # FastAPI エントリポイント
│   ├── routers/           # ルーター群
│   ├── services/          # ビジネスロジック
│   └── templates/         # Jinja2 テンプレート
├── electron/              # Electron シェル（後日実装）
├── tests/
│   ├── unit/              # pytest 単体テスト
│   └── e2e/               # Playwright E2E テスト
├── schema.hcl             # Atlas DB スキーマ定義
├── pyproject.toml
├── .pre-commit-config.yaml
├── README.md
└── LICENSE
```

---

## pyproject.toml

### 本番依存

| パッケージ | 用途 |
|-----------|------|
| fastapi | Web フレームワーク |
| uvicorn[standard] | ASGI サーバー |
| pygit2 | Git 操作（libgit2 バインディング） |
| watchdog | ファイルシステム監視 |
| jinja2 | SVG / HTML テンプレート生成 |

SQLite は stdlib の `sqlite3` を使用するため依存に含めない。

### 開発依存（`[dependency-groups] dev`）

| パッケージ | 用途 |
|-----------|------|
| pytest | 単体テストランナー |
| pytest-cov | カバレッジ計測 |
| pytest-playwright | Playwright pytest プラグイン |
| playwright | E2E テスト |
| taskipy | タスクランナー |
| ruff | Lint / Format |
| ty | 型チェック（Astral 製） |
| pre-commit | コミット前ゲート |

### taskipy タスク

| タスク名 | コマンド | 説明 |
|---------|---------|------|
| `dev` | `uvicorn backend.main:app --reload --port 8000` | 開発サーバー起動 |
| `test` | `pytest tests/unit -v` | 単体テスト |
| `test:e2e` | `pytest tests/e2e -v` | E2E テスト |
| `lint` | `ruff check .` | Lint |
| `format` | `ruff format .` | フォーマット |
| `typecheck` | `ty check` | 型チェック |
| `migrate` | `atlas schema apply --url 'sqlite://${DB_PATH:-dev.db}' --to 'file://schema.hcl' --dev-url 'sqlite://dev?mode=memory'` | DB マイグレーション（開発時は `dev.db`） |
| `build` | `echo 'TODO: Electron build'` | ビルド（後日実装） |

### ruff 設定

- `line-length = 100`
- `select = ["E", "F", "C901"]`
- `max-complexity = 10`（認知的複雑度・循環複雑度ともに 10 以下）

---

## .pre-commit-config.yaml

3 つのフックグループを設定する。

1. **ruff-pre-commit** — `ruff`（lint + 自動修正）、`ruff-format`
2. **local** — `ty check`（型チェック）
3. **pre-commit-hooks** — `trailing-whitespace`、`end-of-file-fixer`、`check-yaml`、`check-toml`

`ty` は公式 pre-commit フックが未安定のため `local` フックで `uv run ty check` を呼ぶ。

---

## DB マイグレーション（Atlas）

- **方式**: 宣言型（Terraform 風）— マイグレーションファイルは管理しない
- **スキーマ定義**: `schema.hcl` に HCL 形式で記述
- **適用コマンド**: `atlas schema apply`（差分を自動計算して適用）
- **インストール**: `brew install ariga/tap/atlas`（Python 依存外）
- SQLite の `ALTER TABLE` 制限は Atlas がテーブル再作成で透過的に対応

---

## README.md

日本語で以下のセクションを含む。

1. プロジェクト概要
2. 技術スタック（表形式）
3. セットアップ（必要環境 + インストール手順）
4. 開発コマンド一覧
5. ライセンス

**インストール手順**:
```bash
uv sync
uv run playwright install chromium
pre-commit install
```

---

## LICENSE

MIT License（著作権者: Tommy109、年: 2026）

---

## 必要環境（README 記載）

| ツール | バージョン | インストール方法 |
|-------|-----------|----------------|
| Python | 3.12+ | uv が自動管理 |
| uv | 最新 | `brew install uv` |
| atlas | 最新 | `brew install ariga/tap/atlas` |
