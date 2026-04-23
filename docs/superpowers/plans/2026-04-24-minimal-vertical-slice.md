# 最小縦スライス Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** リポジトリ登録 → pygit2 による SQLite 同期 → サーバー生成 SVG + htmx でコミット詳細を表示する、までを一気通貫で動かす。

**Architecture:** FastAPI（`backend/`）が SQLite を永続化し、同期は HEAD 基準のトポロジカル走査でコミット・親子・ローカルブランチ先端を書き込む。UI は Jinja2 テンプレートと htmx のみ。クライアント JS は使わない。

**Tech Stack:** Python 3.12、FastAPI、Jinja2、pygit2、SQLite（stdlib）、htmx（CDN 読込）、pytest、pytest-playwright

---

## ファイルマップ

| ファイル | 役割 |
|---------|------|
| `docs/architecture.md` | D3/subprocess/health 表記の整合、`backend/` 構成への更新 |
| `.cursor/rules/*.mdc` | Cursor エージェント向けプロジェクト規約 |
| `.vscode/settings.json` | エディタ・Ruff・pytest 設定 |
| `.cursor/skills/implement/SKILL.md` | 実装手順（backend パス） |
| `.cursor/skills/test-write/SKILL.md` | テスト手順 |
| `backend/paths.py` | DB ディレクトリ（`GIT_LANES_DATA_DIR` 対応） |
| `backend/repositories/ddl.py` | SQLite DDL（IF NOT EXISTS） |
| `backend/repositories/cache_repo.py` | SQLite CRUD |
| `backend/repositories/git_repo.py` | pygit2 走査・ブランチ列挙 |
| `backend/services/sync_service.py` | フル再同期オーケストレーション |
| `backend/services/graph_layout.py` | 単レーン座標 |
| `backend/routers/api.py` | `POST /api/repos` |
| `backend/routers/html.py` | `/`、`/repos/...` |
| `backend/main.py` | アプリ組み立て・静的ファイル |
| `backend/templates/*.html` | ウェルカム・グラフ・詳細断片 |
| `static/css/style.css` | 最低限のレイアウト |
| `schema.hcl` | Atlas 用スキーマ（ドキュメント／migrate 用に拡張） |
| `tests/unit/...` | 同期・レイアウト |
| `tests/integration/...` | TestClient |
| `tests/e2e/conftest.py` | `GIT_LANES_DATA_DIR` をサーバに渡す |
| `tests/e2e/test_graph_smoke.py` | 登録→グラフ |

---

### Task 1: 設計ドキュメントと本計画のコミット

- [ ] **Step 1:** `docs/superpowers/specs/2026-04-24-cursor-docs-minimal-slice-design.md` と本ファイルを追加する
- [ ] **Step 2:** `git commit`

---

### Task 2: ドキュメントと Cursor/VSCode 整備

- [ ] **Step 1:** `docs/architecture.md` を整合させる
- [ ] **Step 2:** `.cursor/rules/` と `.cursor/skills/`、`.vscode/settings.json` を追加する
- [ ] **Step 3:** `git commit`

---

### Task 3: バックエンド縦スライス実装

- [ ] **Step 1:** DDL・キャッシュ・Git 走査・同期・レイアウトを実装する
- [ ] **Step 2:** ルーター・テンプレート・静的 CSS を接続する
- [ ] **Step 3:** `schema.hcl` と README を更新する
- [ ] **Step 4:** `ruff` / `ty` / `pytest` / E2E を実行する
- [ ] **Step 5:** `git commit`
