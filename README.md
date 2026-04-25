# Git Lanes

Git リポジトリのブランチ構造を可視化する Mac デスクトップアプリ。

## 技術スタック

| 役割 | 技術 |
| --- | --- |
| バックエンド | Python 3.12+ / FastAPI |
| Git 操作 | pygit2 |
| FS 監視 | watchdog |
| DB | SQLite（起動時 DDL + Atlas 宣言型 `schema.hcl`） |
| SVG / HTML 生成 | Jinja2 |
| フロントエンド | htmx + hyperscript |
| E2E テスト | Playwright（Python） |
| デスクトップシェル | Electron（予定） |

## 必要環境

| ツール | インストール方法 |
| --- | --- |
| uv | `brew install uv` |
| atlas | `brew install ariga/tap/atlas` |

## セットアップ

```bash
uv sync
uv run playwright install chromium
pre-commit install
pre-commit install --hook-type post-checkout
```

## 開発コマンド

```bash
uv run task dev        # FastAPI 開発サーバー起動（http://localhost:8000）
uv run task test       # 単体・結合テスト（pytest）
uv run task test:e2e   # E2E テスト（Playwright）
uv run task lint       # Lint（ruff）
uv run task format     # フォーマット（ruff）
uv run task typecheck  # 型チェック（ty）
uv run task migrate    # DB マイグレーション（Atlas）
```

## 最小縦スライス（Web UI）

1. `uv run task dev` でサーバーを起動する。
2. ブラウザで `http://127.0.0.1:8000/` を開き、ローカル Git リポジトリの**ディレクトリパス**をフォームに入力して送信する。
3. グラフ画面でコミットノードをクリックすると、htmx で右ペインに詳細が表示される。

テストや E2E では SQLite を作業用ディレクトリに置くため、**`GIT_LANES_DATA_DIR`**（絶対パス推奨）を設定する。`tests/e2e/conftest.py` のサーバ起動でも同変数を渡している。

## Cursor 向け

- プロジェクトルール: `.cursor/rules/*.mdc`
- 実装・テスト用スキル: `.cursor/skills/`
- エディタ共有設定: `.vscode/settings.json`

## ライセンス

MIT
