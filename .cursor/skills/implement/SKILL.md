---
name: implement
description: Git Lanes プロジェクトのコーディング規約に従って実装する。関数・ファイル行数・複雑度・ドックストリング・コメント言語を自動チェックしながら進める。
type: rigid
---

# Git Lanes 実装スキル（Cursor）

このスキルは実装のたびに参照し、すべての制約を満たすことを確認する。

## 実装前の確認

変更対象のファイルを Read して現状の行数を把握する。
150 行に近いファイルに追記する場合は、先に分割を検討する。

## 実装中のルール

### 関数を書くたびに確認する

```
□ 30 行以内か？
  → 超える場合はヘルパー関数に切り出す

□ 分岐（if / for / while / try）のネストは 3 段以内か？
  → 深い場合はガード節（早期 return）または関数分割で解消する

□ Google スタイルのドックストリングがあるか？（日本語）
  → Args / Returns / Raises を必要な分だけ記載する

□ コメントは日本語か？
  → 英語コメントは書かない
```

### ファイルを保存するたびに確認する

```
□ 150 行以内か？（テストコードは対象外）
  → 超える場合はモジュールを分割する

□ D3.js を import していないか？
  → SVG は Jinja2 テンプレートで生成する

□ 手書きの JavaScript を増やしていないか？
  → htmx 属性と必要なら hyperscript（_="..."）で表現する

□ subprocess で git コマンドを呼んでいないか？
  → pygit2 の API を使う
```

## アーキテクチャ上の制約

- **SQLite**: 現状は `backend/paths.primary_db_path()`（`GIT_LANES_DATA_DIR` で上書き可）。将来シャード化する場合はここを拡張する。
- **SVG / htmx**: クライアントでグラフを結合しない。サーバーが返した断片を差し替える。

## 実装後のセルフチェック

```bash
uv run ruff format backend tests
uv run ruff check --fix backend tests
uv run ty check backend
uv run task test
uv run task test:e2e
```

問題があれば修正してから PR / コミットに進む。
