# Git Lanes - Claude 向けプロジェクトルール

## プロジェクト概要

Git リポジトリのブランチ構造を可視化する Mac デスクトップアプリ。
pywebview が FastAPI（Python）をサブプロセスとして内包し、`.app` として配布する。
SQLite キャッシュと watchdog による差分更新で、大規模リポジトリでも高速に動作させることが目的。

## 技術スタック（クイックリファレンス）

| 役割 | 技術 |
| --- | --- |
| デスクトップシェル | pywebview（macOS WKWebView） |
| バックエンド | Python 3.12+ / FastAPI |
| Git 操作 | pygit2（libgit2 バインディング） |
| FS 監視 | watchdog（FSEvents 使用） |
| DB | SQLite（`~/Library/Application Support/git-lanes/<repo-id>.db`） |
| ORM / クエリ層 | SQLModel（SQLAlchemy + Pydantic ベース） |
| SVG 生成 | Jinja2 テンプレート（サーバーサイド生成、D3.js は使わない） |
| CSS フレームワーク | LismCSS（レイアウトプリミティブ・MCP サーバーあり） |
| フロントエンド | htmx 2.x + hyperscript 0.9.x |
| E2E テスト | Playwright（Python） |
| タスクランナー | taskipy（`uv run task <name>`） |
| Lint / Format | Ruff（Rust 実装） / ty（型チェック） |
| MD Lint | markdownlint-cli2 |
| コミット前ゲート | pre-commit |

## タスク実行コマンド

```bash
uv run task dev        # FastAPI 開発サーバー起動
uv run task app        # pywebview アプリ起動
uv run task test       # 単体・統合テスト（pytest）
uv run task test:e2e   # E2E テスト（Playwright）
uv run task lint       # ruff check
uv run task format     # ruff format
uv run task typecheck  # ty check（型チェック）
uv run task lint:md    # markdownlint-cli2（グローバルインストール前提）
uv run task migrate    # Atlas で DB スキーマを適用
uv run task build      # Mac 向け .app ビルド
```

## コード品質の制約（必須・例外なし）

| 制約 | 基準 | 測定ツール |
| --- | --- | --- |
| 認知的複雑度 | 10 以下 | Ruff C901 |
| 循環複雑度（代替） | 10 以下 | Ruff mccabe |
| 関数の行数 | 30 行以内 | レビュー |
| ファイルの行数 | 150 行以内（テスト除く） | CI チェック |

制約を超える場合は実装を分割する。「後でリファクタリング」は認めない。

## Python コーディング規約

### ドックストリング（Google スタイル・日本語）

```python
def get_commits(repo_path: str, limit: int = 50) -> list[Commit]:
    """指定リポジトリから最新コミットを取得する。

    Args:
        repo_path: Git リポジトリのパス。
        limit: 取得するコミットの上限数。

    Returns:
        コミット情報のリスト。新しい順に並ぶ。

    Raises:
        RepositoryNotFoundError: リポジトリが存在しない場合。
    """
```

### コメント

- **プロダクトコード・テストコードともに日本語のみ**
- 自明な処理にはコメントを書かない（何をしているかではなく、なぜを書く）

## テストの書き方

### 単体テスト（pytest・AAA スタイル）

```python
def test_parse_commit_hash_returns_short_hash():
    # --- Arrange ---
    raw_hash = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"

    # --- Act ---
    result = parse_commit_hash(raw_hash)

    # --- Assert ---
    assert result == "a1b2c3d"
```

### E2E テスト（pytest-playwright・ガーキン記法）

```python
def test_スクロールで過去コミットが追加表示される(page: Page, base_url: str):
    # Given: グラフ画面が表示されている状態
    page.goto(f"{base_url}/graph/1")
    page.wait_for_selector(".commit-node")

    # When: ページ末尾までスクロールして先読みページが表示域に入る
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_function(
        "document.querySelectorAll('.commit-page:not([hidden])').length > 1"
    )

    # Then: グラフに追加コミットが表示される
    assert page.locator(".commit-page:not([hidden])").count() == 2
```

- ガーキンキーワード（Given / When / Then）は英語のまま
- 説明文・コメントは日本語

### カバレッジ目標

- 単体テスト: **85〜90%**（意味のあるテストケースのみ）
- E2E: ハッピーパスと操作制御（disable/enable）に集中

## コミット・PR 規約

### コミット前の必須確認（作業メモリに頼らない）

コミットを実行する前に、**必ず以下のコマンドで実際の変更内容を確認する**。
セッション中の記憶や作業ログは参照してはならない。

```bash
git status          # 変更ファイルの一覧と現在のブランチを確認
git diff            # 未ステージの変更を確認
git diff --staged   # ステージ済みの変更を確認
```

- 現在のブランチが意図したブランチであることを `git status` で確認してからコミットする
- `-C <path>` で別ディレクトリを指定する場合は、そのブランチが正しいかを必ず確認する

### コミットメッセージ（Conventional Commits + 日本語）

```
<type>: <日本語の件名>

<日本語の本文（任意）>
```

| type | 用途 |
| --- | --- |
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `refactor` | リファクタリング |
| `test` | テスト追加・修正 |
| `docs` | ドキュメントのみ |
| `chore` | ビルド・設定変更 |
| `perf` | パフォーマンス改善 |

### プルリクエスト

- タイトルは Conventional Commits 形式（例: `feat: ブランチフィルタを追加する`）で日本語
- 本文には「変更の目的」「動作確認方法」「スクリーンショット（UI 変更時）」を含める

## pre-commit フックの設計方針

- **コミット時にブロック（必須）**: `ruff check`・`ruff format`・単体テスト（`tests/unit`）
- **CI のみ（コミット時は非実行）**: 統合テスト・E2E テスト（実行時間が長いため）

## アーキテクチャの重要な決定事項

1. **JavaScript は最小限** — htmx + hyperscript で完結させる。`app.js` は原則不要
2. **SQLite はリポジトリごとに 1 ファイル** — `~/Library/Application Support/git-lanes/<repo-id>.db`
3. **rebase / force push 対応** — 差分更新前に `cached_head` が現 HEAD の祖先かを確認し、そうでなければ全件再取得する
4. **Python 同梱** — uv ポータブル Python を pywebview アプリバンドルに含める
5. **Git 操作は pygit2 のみ** — subprocess で git コマンドを叩かない

## ドキュメント

詳細は `docs/` を参照する。

- `docs/specification.md` — 製品仕様・機能要件
- `docs/technology.md` — 技術選定理由・コーディング規約
- `docs/architecture.md` — システム構成・データフロー・DB 設計

<!-- dagayn MCP tools -->
## MCP Tools: dagayn

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
dagayn MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.

<!-- dagayn markdown policy -->
## Markdown documentation policy: declare dependencies via directive comments

When authoring or editing a Markdown document in this repository, declare
inter-section and inter-document dependencies as HTML directive comments so
they are captured by the dagayn graph (`DEPENDS_ON` / `IMPORTS_FROM` edges)
and discoverable via `query_graph` / `get_impact_radius`.

### Required form

```markdown
<!-- <kind> <target> -->
```

`<kind>` MUST be one of: `constrained-by`, `blocked-by`, `supersedes`,
`derived-from`. Choose the kind whose semantics best match the dependency:

| Kind | Use when |
| ---- | -------- |
| `constrained-by` | This section's design is bounded by the referenced document/section |
| `blocked-by` | This item cannot proceed until the referenced item resolves |
| `supersedes` | This document replaces the referenced content |
| `derived-from` | This section is derived from the referenced source |

### Three target shapes

| Dependency type | Target syntax | Example |
| --------------- | ------------- | ------- |
| Within-document section | `#section-slug` | `<!-- derived-from #background -->` |
| Other document (whole file) | `./relative/path.md` | `<!-- blocked-by ./specs/open-issue.md -->` |
| Other document + section | `./path.md#slug` | `<!-- constrained-by ./adr.md#context -->` |

Slugs follow GitHub Markdown rules: lowercase, non-alphanumerics removed,
spaces and hyphens collapsed to `-`. Place the directive immediately under
the heading whose content depends on the target. External URLs
(`http://`, `https://`) are not graph-resolvable — keep them as ordinary
Markdown links, not directive targets.

### When to add a directive

- Section design references an ADR, spec, or research note → `constrained-by` or `derived-from`.
- A document replaces an older one → `supersedes` (place in the new document).
- A spec/task section is blocked on another being resolved → `blocked-by`.
- A later section extends an earlier one non-obviously → `derived-from #earlier-section`.

If no real dependency exists, do not invent one. Directives are signal, not decoration.
