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
