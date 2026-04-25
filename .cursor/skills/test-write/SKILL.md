---
name: test-write
description: Git Lanes のテストを書く。単体は AAA（pytest・日本語コメント）、E2E はガーキン（Playwright・日本語コメント）。
type: rigid
---

# Git Lanes テスト作成スキル（Cursor）

## 単体・結合（pytest）

- 配置: `tests/unit/`、`tests/integration/`。パスは **`backend/`** をインポートする。
- スタイル: **AAA**（Arrange / Act / Assert）をコメントで区切る。
- SQLite を触る場合は **`GIT_LANES_DATA_DIR`** を `tmp_path` に向け、**`closing(connect(...))`** で接続を閉じる。
- コメントは**日本語**。

## E2E（pytest-playwright）

- 配置: `tests/e2e/`。**Given / When / Then** は英語キーワード、説明は日本語。
- サーバ fixture（`conftest.py`）は **`GIT_LANES_DATA_DIR`** を環境変数で渡す。
- ハッピーパスと主要な操作制御に集中する（ロジックの網羅は単体へ）。

## 実行コマンド

```bash
uv run task test
uv run task test:e2e
```
