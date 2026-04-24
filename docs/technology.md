# Git Lanes - 技術スタック

## 採用技術一覧

| レイヤー | 技術 | バージョン目安 | 役割 |
| --- | --- | --- | --- |
| デスクトップシェル | Electron | 32+ | Mac アプリ化・FastAPI サブプロセス管理 |
| バックエンド | Python | 3.12+ | ビジネスロジック・Git 操作 |
| Web フレームワーク | FastAPI | 0.115+ | REST API + HTML レスポンス |
| Git 操作 | pygit2 | 1.x | libgit2 経由の Git リポジトリ操作 |
| FS 監視 | watchdog | 4.x | FSEvents を用いたリポジトリ変更検知 |
| データベース | SQLite | 3.x | グラフデータのキャッシュ（リポジトリごとに 1 ファイル） |
| ORM / クエリ層 | SQLModel | 0.0.21+ | SQLAlchemy + Pydantic ベースの型安全 ORM |
| フロントエンド（SVG 生成） | Jinja2 | 3.x | サーバーサイドで SVG を生成してレスポンスに含める |
| フロントエンド（インタラクション） | htmx | 2.x | サーバードリブンな部分更新・先読みスクロール |
| フロントエンド（クライアント挙動） | hyperscript | 0.9.x | htmx と連携するクライアントサイドのスクリプト |
| E2E テスト | Playwright | 1.x | ブラウザ自動操作による E2E テスト |
| タスクランナー | taskipy | — | テスト・dev 起動などの開発タスク管理 |
| コミット前品質ゲート | pre-commit | — | コミット前に lint・format・テストを自動実行 |
| 静的解析・フォーマット | Rust ベースツール | — | コード品質の維持 |
| Markdown Lint | markdownlint-cli2 | — | Markdown ドキュメントの品質チェック |

---

## 各技術の選定理由

### Electron

- Web 技術（HTML / CSS / JS）をそのまま Mac デスクトップアプリとして配布できる
- `electron-builder` で Apple Silicon / Intel の Universal バイナリを生成できる
- メインプロセスが Python（FastAPI）サーバーをサブプロセスとして起動・終了を管理し、ポートを決定してから `BrowserWindow` をロードする
- ネイティブダイアログ（`dialog.showOpenDialog`）でフォルダ選択ができ、OS との統合が自然

### Python + FastAPI

- FastAPI は Jinja2 テンプレートによる HTML / SVG レスポンスと JSON API を同一サーバーで提供できる
- 非同期 I/O により SQLite アクセスと Git 操作を効率よく処理できる

### pygit2

- libgit2（C ライブラリ）への Python バインディングで、高速かつ安定している
- `git log` のトポロジカル順序走査・親コミット取得・ブランチ列挙を API として提供する
- ネイティブビルドが必要なため、uv ポータブル環境への組み込み時は事前検証が必要

### watchdog

- Python 製のファイルシステム監視ライブラリ。macOS では内部的に FSEvents を使用する
- `.git/refs/` と `.git/HEAD` を監視し、変更イベントをコールバックで受け取る
- Git 組み込みの `core.fsmonitor` は Git 自身の高速化用であり外部利用には使えないため、watchdog を採用する

### SQLite

- ファイルベースの永続化。リポジトリごとに 1 ファイルを `~/Library/Application Support/git-lanes/` に配置する
- コミットグラフの差分更新クエリ（INSERT OR IGNORE）が高速
- ファイル単位でバックアップ・削除が容易

### SQLModel

- FastAPI と同じ Tiangolo が開発した ORM で、Pydantic モデルと SQLAlchemy の統合を提供する
- テーブル定義・バリデーション・API スキーマを単一の `SQLModel` クラスで表現でき、型アノテーションが仕様書の役割を兼ねる
- FastAPI の依存注入（`Depends`）との親和性が高く、セッション管理が簡潔になる
- SQLite への接続は SQLAlchemy エンジン経由のため、将来のデータベース移行も容易

### Jinja2（SVG 生成）

- FastAPI が既に依存しているため追加ライブラリ不要
- ブランチレーンの座標計算は Python で行い、結果を Jinja2 テンプレートで SVG に変換する
- 専用の Python グラフライブラリは不要。D3.js も不要
- 1 ページ 50 コミットという規模ではサーバーサイド SVG 生成で十分な速度が出る

### htmx + hyperscript

- ページ全体を JS で管理せず、サーバーが HTML / SVG の断片を返すアーキテクチャにできる
- `hx-trigger="intersect"` による先読みスクロール（次ページを hidden で先行取得し、表示域に入った時点で visible 化）が容易
- **hyperscript** は htmx の同作者が開発したクライアントサイドスクリプト言語で、`_="..."` 属性に直接記述する
- `classList`・`toggle`・イベントハンドリングなど、htmx だけでは対応しにくい局所的なDOM操作を JavaScript を書かずに表現できる
- `app.js` を持たずに済み、ロジックが HTML に局所化されるため見通しが良い

**役割分担の例:**

| 操作 | 担当 |
| --- | --- |
| サーバーへのリクエスト・HTML 断片の差し込み | htmx |
| hidden の除去・クラスの付け替え・トグル操作 | hyperscript |
| 複雑なイベント処理が必要な場面（将来） | 最小限の `app.js` |

### Playwright

- Python バインディング（`pytest-playwright`）を使用し、FastAPI の Web UI をブラウザ経由でテストする
- Electron 対応は後日追加する（`_electron.launch()` を使用予定）
- ボタンの `disabled` 属性や aria 状態の検証が容易で、E2E 重点項目（操作制御）と相性が良い
- `pytest-playwright` の `page` fixture により htmx の非同期 DOM 更新を自動待機できる

---

## Rust ベースの静的解析・フォーマッタ

### 採用ツール

| ツール | 対象言語 | 用途 |
| --- | --- | --- |
| [Ruff](https://github.com/astral-sh/ruff) | Python | リント・フォーマット（Rust 実装） |
| [ty](https://github.com/astral-sh/ty) | Python | 型チェック（Rust 実装・Astral 製） |
| [rustfmt](https://github.com/rust-lang/rustfmt) | Rust（将来採用時） | フォーマット |

> Ruff は Rust で実装されており、flake8・isort・black の役割を単一ツールで担う。

### コード品質の数値基準

| 指標 | 目標値 | 測定ツール |
| --- | --- | --- |
| 認知的複雑度 | 10 以下 | Ruff (`C901` ルール相当) |
| 循環複雑度（認知的複雑度が測定不能な場合） | 10 以下 | Ruff `mccabe` |
| 関数の行数 | 30 行以内 | Ruff カスタムルール / レビュー |
| ファイルの行数 | 150 行以内（テストコードを除く） | Ruff / CI チェック |

---

## Python コーディング規約

### ドックストリング

Google スタイルを採用する。

```python
def get_commits(repo_path: str, limit: int = 50) -> list[Commit]:
    """指定リポジトリから最新コミットを取得する。

    Args:
        repo_path: Git リポジトリのパス。
        limit: 取得するコミットの上限数。デフォルトは 50。

    Returns:
        コミット情報のリスト。新しい順に並ぶ。

    Raises:
        RepositoryNotFoundError: 指定パスにリポジトリが存在しない場合。
    """
```

### コメント

- プロダクトコード・テストコードともに **日本語** でコメントを記述する
- 自明な処理にはコメントを書かない。「なぜ」が非自明な場合のみ記述する

---

## テストコードの構造

### 単体テスト（AAA スタイル）

```python
def test_parse_commit_hash_returns_short_hash():
    # --- Arrange ---
    raw_hash = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"

    # --- Act ---
    result = parse_commit_hash(raw_hash)

    # --- Assert ---
    assert result == "a1b2c3d"
```

### 統合テスト・E2E テスト（ガーキン記法）

E2E テストは **Playwright** を使用する。`playwright/test` の `test` / `expect` を用い、コメントでガーキン記法のブロックを示す。

```typescript
test("スクロールで過去コミットが追加表示される", async ({ page }) => {
    // Given: Git Lanes が起動し、初期グラフが表示されている状態
    await page.goto("/");
    await page.waitForSelector(".commit-node");

    // When: ページ末尾までスクロールして先読みページが表示域に入る
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForFunction(
        () => document.querySelectorAll(".commit-page:not([hidden])").length > 1
    );

    // Then: グラフに追加コミットが表示される
    const pages = page.locator(".commit-page:not([hidden])");
    await expect(pages).toHaveCount(2);
});
```

Electron アプリを直接テストする場合は `_electron.launch()` を使用する。

```typescript
import { _electron as electron } from "playwright";

test("アプリが起動してグラフが表示される", async () => {
    // Given: Electron アプリを起動する
    const app = await electron.launch({ args: ["electron/main.js"] });
    const window = await app.firstWindow();

    // When: グラフページが読み込まれる
    await window.waitForSelector(".commit-node");

    // Then: コミットノードが 1 件以上表示されている
    await expect(window.locator(".commit-node").first()).toBeVisible();

    await app.close();
});
```

---

## パッケージ管理・タスクランナー

- Python: `uv`（高速リゾルバ）を使用し、`pyproject.toml` で依存を管理する
- Electron / フロントエンド: `npm` で管理し、`package.json` に依存を記述する
- 開発タスク: **taskipy** を使用する。テスト実行・dev サーバー起動・ビルドなど、すべての開発コマンドを `taskipy` 経由で統一する

### taskipy タスク例

| タスク名 | 内容 |
| --- | --- |
| `dev` | FastAPI 開発サーバーを起動する |
| `electron` | Electron アプリを開発モードで起動する |
| `test` | pytest で単体テスト・統合テストを実行する |
| `test:e2e` | Playwright で E2E テストを実行する |
| `lint` | `ruff check` でリントを実行する |
| `format` | `ruff format` でフォーマットを実行する |
| `lint:md` | `markdownlint-cli2` で Markdown をチェックする |
| `build` | Electron アプリを Mac 向けにビルドする |

---

## コミット・PR 規約

### コミットメッセージ

**Conventional Commits** に準拠する。ただし内容（件名・本文）は**日本語**で記述する。

```
<type>: <日本語の件名>

<日本語の本文（任意）>
```

**主な type 一覧:**

| type | 用途 |
| --- | --- |
| `feat` | 新機能の追加 |
| `fix` | バグ修正 |
| `refactor` | 機能変更を伴わないリファクタリング |
| `test` | テストコードの追加・修正 |
| `docs` | ドキュメントのみの変更 |
| `chore` | ビルド・設定ファイルなどの変更 |
| `perf` | パフォーマンス改善 |

**例:**

```
feat: ブランチグラフの先読みスクロールを実装する

スクロール位置が次ページ先頭に達した時点で hidden を外し、
続けて次の次ページを先読みする仕掛けを追加した。
```

### プルリクエスト

- タイトル・本文ともに**日本語**で記述する
- タイトルは Conventional Commits の形式に合わせる（`feat: ブランチフィルタを追加する` など）
- 本文には「変更の目的」「動作確認方法」「スクリーンショット（UI 変更時）」を含める

---

## pre-commit フック

`.pre-commit-config.yaml` でフックを定義し、`git commit` のたびに自動実行する。

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.x.x
    hooks:
      - id: ruff          # リント（自動修正あり）
        args: [--fix]
      - id: ruff-format   # フォーマット

  - repo: local
    hooks:
      - id: pytest-unit
        name: unit tests
        entry: uv run pytest tests/unit
        language: system
        pass_filenames: false
```

### フックの設計方針

- **必須（ブロッキング）**: `ruff check`・`ruff format` — 形式不備のコミットを防ぐ
- **必須（ブロッキング）**: 単体テスト（`tests/unit`）— ロジックの退行を防ぐ
- **対象外**: 統合テスト・E2E テスト — 実行時間が長いため CI のみで実行する

---

## CI チェック項目

1. `ruff check` — リント
2. `ruff format --check` — フォーマット
3. `pytest --cov` — テスト & カバレッジ（85% 以上を必須とする）
4. ファイル行数チェック（150 行超を検出するシェルスクリプト）
5. `npx playwright test` — E2E テスト実行
6. `npm run build` — Electron アプリのビルド確認
7. `electron-builder --mac` — Mac 向け `.app` バンドル生成の確認
