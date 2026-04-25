# Cursor 整備・ドキュメント整合・最小縦スライス 設計書

**作成日**: 2026-04-24
**前提**: D3.js は使用しない。SVG はサーバー（Jinja2）で断片生成し、htmx で DOM を更新する。Git 操作は pygit2 のみ。実行基盤（uv / taskipy / ruff / ty / Playwright）は構築済み。

---

## 1. ドキュメント整合（`docs/architecture.md`）

### 1.1 修正方針

- **クライアント側 D3.js 記述の削除**: 増分ロードは htmx の swap でサーバーが返した HTML/SVG 断片を挿入する。クライアントでグラフを結合・再レイアウトしない。
- **Git 取得表現の統一**: `git log` など CLI 前提の文言をやめ、**pygit2 での走査**（本番では全参照を対象にしたトポロジカル走査が最終形）と明記する。最小縦スライスでは **HEAD からのトポロジカル走査**に限定し、仕様上の全ブランチ対応は後続とする。
- **ヘルスチェック**: 実装・テストは `/health` のため、Electron 起動フローの記述を **`/health` に統一**する。
- **ディレクトリ構成**: 実リポジトリは **`backend/`** 配下に FastAPI があるため、図を現状に合わせる。
- **エラー・セキュリティ文言**: 「Git コマンド失敗」→ **pygit2 / リポジトリ操作の失敗**へ。`subprocess` は **Git には使わない**ことを明確化し、Electron がサーバーを起動するなど **必要な subprocess は引数リスト形式**と整理する。

---

## 2. Cursor 向け整備

### 2.1 `.cursor/rules/`（`.mdc`）

- **常時適用**: Python 品質（ruff / ty / 複雑度・行数・日本語 docstring/コメント）、アーキテクチャ制約（D3 不使用、サーバー SVG + htmx、pygit2 のみ）。
- **`docs/**/*.md` 用**: 仕様・技術・アーキテクチャ間の矛盾を避ける注意、`markdownlint-cli2 --fix` の実行を明記。

### 2.2 `.vscode/settings.json`

- 保存時フォーマット、Ruff を既定フォーマッタに、pytest 探索、Markdown 向けの最低限のエディタ設定。

### 2.3 `.cursor/skills/`

- `.claude/skills` の内容を **このリポジトリ向けにパス表記を `backend/` に合わせた** Cursor 用スキルとして配置する（実装・テスト作成の手順をエージェントが参照できるようにする）。

---

## 3. 最小縦スライス（MVP）

### 3.1 スコープ（含む）

- リポジトリ登録（フォーム POST → 登録後グラフへリダイレクト）。
- **初回・HEAD 移動時はフル再同期**（該当 `repo_id` のコミット関連行を削除して再投入）。watchdog による差分同期・rebase 検知の本実装は後続。
- SQLite 永続化（本番想定パスは `~/Library/Application Support/git-lanes/` 配下の **`git-lanes.db` 単一ファイル**（最小縦スライス）。**テスト/E2E 用に `GIT_LANES_DATA_DIR` で上書き可能**にする）。将来リポジトリ別 `.db` へシャード化する場合は `backend/paths.py` を拡張する。
- 単レーン縦レイアウトの **SVG** と、コミットクリックで **htmx** により右ペイン更新。
- 単体テスト（同期・レイアウト）、結合テスト（TestClient）、E2E（登録→グラフ表示のスモーク）。

### 3.2 スコープ（含まない）

- 先読み無限スクロール、ブランチフィルタ、リモート表示、タグ、Electron シェル、Atlas 必須での CI スキーマ適用（アプリは起動時に DDL を `CREATE TABLE IF NOT EXISTS` で整合）。

### 3.3 主要エンドポイント

- `GET /` — ウェルカム（パス入力フォーム）。
- `POST /api/repos` — `path`（フォーム）を受け取り登録、`303` で `/repos/{id}/graph` へ。
- `GET /repos/{repo_id}/graph` — 同期後、直近 50 コミットのグラフ HTML。
- `GET /repos/{repo_id}/commits/{commit_hash}/detail` — 右ペイン用 HTML 断片（htmx）。

### 3.4 データモデル

- `docs/architecture.md` の `repositories` / `commits` / `commit_parents` / `branches` に準拠。`repositories` に `cached_head` / `synced_at` を持つ。

### 3.5 テスト方針

- **単体**: pygit2 でテンポラリリポジトリを生成し、同期後に SQLite の行数・代表値を検証。
- **結合**: `GIT_LANES_DATA_DIR` を一時ディレクトリに向け、`TestClient` で登録→グラフ取得。
- **E2E**: セッションサーバの環境変数に `GIT_LANES_DATA_DIR` を渡し、フォーム POST → レスポンスにグラフ要素が含まれることを確認。

---

## 4. 自己レビュー

- プレースホルダ・TBD なし。
- D3 不使用・htmx 更新・pygit2 のみ、と本文・CLAUDE.md と整合。
- スライスは「同期+表示」の縦断に限定し、watchdog 等は明確に後続化。
