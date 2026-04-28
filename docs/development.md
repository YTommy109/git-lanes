# 開発者ガイド

このドキュメントでは、Git Lanes の開発環境のセットアップと開発ワークフローについて説明します。

## 技術スタック

| 役割 | 技術 |
| --- | --- |
| バックエンド | Python 3.12+ / FastAPI |
| Git 操作 | pygit2 |
| FS 監視 | watchdog |
| DB | SQLite（SQLModel / Atlas 宣言型 `schema.hcl`） |
| SVG / HTML 生成 | Jinja2 |
| フロントエンド | htmx + hyperscript |
| CSS フレームワーク | LismCSS |
| E2E テスト | Playwright（Python） |
| デスクトップシェル | pywebview |

## 開発環境の要件

| ツール | インストール方法 |
| --- | --- |
| uv | `brew install uv` |
| atlas | `brew install ariga/tap/atlas` |
| markdownlint-cli2 | `brew install markdownlint-cli2` |

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
uv run task app        # pywebview アプリ起動
uv run task test       # 単体・結合テスト（pytest）
uv run task test:e2e   # E2E テスト（Playwright）
uv run task lint       # Lint（ruff）
uv run task format     # フォーマット（ruff）
uv run task typecheck  # 型チェック（ty）
uv run task migrate    # DB マイグレーション（Atlas）
uv run task lint:md    # Markdown の Lint（markdownlint-cli2）
uv run task build      # Mac 向け .app ビルド
```

### 環境変数

テストや E2E では SQLite を作業用ディレクトリに置くため、**`GIT_LANES_DATA_DIR`**（絶対パス推奨）を設定してください。

## 開発用 Web UI の確認方法

1. `uv run task dev` でサーバーを起動します。
2. ブラウザで `http://127.0.0.1:8000/` を開き、ローカル Git リポジトリの**ディレクトリパス**をフォームに入力して送信します。
3. グラフ画面でコミットノードをクリックすると、htmx で右ペインに詳細が表示されます。

## リリース手順

```bash
uvx bump-my-version bump patch   # patch バージョンを上げる（minor / major も同様）
git push && git push --tags      # GitHub Actions が発火して DMG 付き Release を作成
```

バージョン番号の種類:

| コマンド | 変更例 |
| --- | --- |
| `bump patch` | `0.1.0` → `0.1.1` |
| `bump minor` | `0.1.0` → `0.2.0` |
| `bump major` | `0.1.0` → `1.0.0` |

## エディタ設定

### Cursor / VS Code

- プロジェクトルール: `.cursor/rules/*.mdc`
- 実装・テスト用スキル: `.cursor/skills/`
- エディタ共有設定: `.vscode/settings.json`

## 詳細ドキュメント

- `CLAUDE.md`: 開発ルール、コーディング規約、詳細なコマンド
- `docs/architecture.md`: アーキテクチャ設計
- `docs/specification.md`: 機能仕様
- `docs/technology.md`: 技術選定の背景
