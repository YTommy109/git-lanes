# CI 環境構築 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub Actions CI ワークフローを追加し、PR マージ前・main push 時に lint/typecheck/test/e2e が必須で通過する環境を構築する。

**Architecture:** `ci.yml` を新規作成して lint-typecheck → test + test-e2e の段階的パイプラインを実装する。`release.yml` は `checkout@v6`（無効なバージョン）を `v4` に修正するのみ。ブランチ保護の設定手順は `docs/github-branch-protection.md` に記載し、GitHub 画面での手動設定をガイドする。

**Tech Stack:** GitHub Actions、astral-sh/setup-uv@v8.1.0、Playwright (chromium)、pytest-cov

---

## ファイル構成

| 操作 | パス | 内容 |
|---|---|---|
| 作成 | `.github/workflows/ci.yml` | CI パイプライン本体 |
| 修正 | `.github/workflows/release.yml:17` | `checkout@v6` → `v4` |
| 作成 | `docs/github-branch-protection.md` | ブランチ保護設定手順 |

---

### Task 1: CI コマンドをローカルで動作確認する

CI ワークフロー作成前に、各コマンドがローカルで通過することを確認する。

**Files:**
- 変更なし（確認のみ）

- [ ] **Step 1: lint チェックが通ることを確認する**

```bash
uv run task lint
```

期待値: `All checks passed.` または変更ファイルなし

- [ ] **Step 2: 型チェックが通ることを確認する**

```bash
uv run task typecheck
```

期待値: エラー 0 件

- [ ] **Step 3: 単体・統合テストとカバレッジが通ることを確認する**

```bash
uv run pytest -v --cov --cov-report=term-missing
```

期待値: 全テスト PASSED、カバレッジ 85% 以上

- [ ] **Step 4: E2E テストが通ることを確認する**

```bash
uv run task test:e2e
```

期待値: 全テスト PASSED（サーバーが自動起動して終了する）

---

### Task 2: `ci.yml` を作成する

**Files:**
- 作成: `.github/workflows/ci.yml`

- [ ] **Step 1: `ci.yml` を作成する**

`.github/workflows/ci.yml` を以下の内容で作成する:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v8.1.0
        with:
          python-version: "3.12"

      - name: 依存パッケージをインストールする
        run: uv sync --group dev --frozen

      - name: Lint チェックを実行する
        run: uv run task lint

      - name: 型チェックを実行する
        run: uv run task typecheck

  test:
    needs: lint-typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v8.1.0
        with:
          python-version: "3.12"

      - name: 依存パッケージをインストールする
        run: uv sync --group dev --frozen

      - name: 単体・統合テストを実行する
        run: uv run pytest -v --cov --cov-report=term-missing

  test-e2e:
    needs: lint-typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v8.1.0
        with:
          python-version: "3.12"

      - name: 依存パッケージをインストールする
        run: uv sync --group dev --frozen

      - name: Playwright ブラウザをインストールする
        run: uv run playwright install --with-deps chromium

      - name: E2E テストを実行する
        run: uv run task test:e2e
```

- [ ] **Step 2: YAML の構文を確認する**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
```

期待値: `YAML OK`

- [ ] **Step 3: コミットする**

```bash
git add .github/workflows/ci.yml
git commit -m "chore: GitHub Actions CI ワークフローを追加する"
```

---

### Task 3: `release.yml` を修正する

**Files:**
- 修正: `.github/workflows/release.yml:17`

- [ ] **Step 1: `checkout@v6` を `v4` に修正する**

`.github/workflows/release.yml` の 17 行目:

```yaml
# 変更前
      - uses: actions/checkout@v6

# 変更後
      - uses: actions/checkout@v4
```

- [ ] **Step 2: YAML の構文を確認する**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" && echo "YAML OK"
```

期待値: `YAML OK`

- [ ] **Step 3: コミットする**

```bash
git add .github/workflows/release.yml
git commit -m "fix: release.yml の actions/checkout バージョンを v4 に修正する"
```

---

### Task 4: ブランチ保護設定ドキュメントを作成する

**Files:**
- 作成: `docs/github-branch-protection.md`

- [ ] **Step 1: `docs/github-branch-protection.md` を作成する**

```markdown
# GitHub ブランチ保護設定手順

main ブランチへのマージ前に CI が必須通過するよう設定する。
初回セットアップ時に一度だけ GitHub の画面で実施する。

## 手順

1. リポジトリの **Settings** タブを開く
2. 左メニューの **Branches** をクリック
3. **Branch protection rules** セクションの **Add rule** をクリック
4. **Branch name pattern** に `main` と入力する

### 必須チェック設定

以下の項目を有効にする:

| 項目 | 設定 |
|---|---|
| Require a pull request before merging | ✅ |
| Require status checks to pass before merging | ✅ |
| Require branches to be up to date before merging | ✅ |
| Do not allow bypassing the above settings | ✅ |

**Status checks** の検索欄で以下の 3 つを追加する（CI が一度でも実行されていれば候補に出る）:

- `lint-typecheck`
- `test`
- `test-e2e`

5. **Create** をクリックして保存する

## 確認方法

設定後、main への PR を作成すると Checks タブに 3 つのジョブが表示される。
すべて ✅ になるまでマージボタンが無効化される。
```

- [ ] **Step 2: コミットする**

```bash
git add docs/github-branch-protection.md
git commit -m "docs: GitHub ブランチ保護設定手順を追加する"
```
