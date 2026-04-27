# GitHub Actions 自動リリース CI/CD 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** タグ `v*.*.*` の push をトリガーに macOS 向け DMG を自動ビルドし GitHub Release に添付する

**Architecture:** GitHub Actions の `macos-latest` ランナー上で uv + PyInstaller でビルドし、`create-dmg` で DMG 化して `softprops/action-gh-release` でリリースに添付する。バージョン管理は `bump-my-version` で `pyproject.toml` と `git_lanes.spec` の 2 箇所を一括更新する。

**Tech Stack:** GitHub Actions, uv, PyInstaller, create-dmg (brew), softprops/action-gh-release@v2, bump-my-version

---

## ファイル構成

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `.github/workflows/release.yml` | 新規作成 | リリースワークフロー本体 |
| `pyproject.toml` | 修正 | `[tool.bumpversion]` 設定を追加 |
| `git_lanes.spec` | 修正 | bump-my-version のターゲット文字列確認（変更なし、設定のみ） |
| `README.md` | 修正 | リリース手順セクションを追加 |

---

### Task 1: GitHub Actions ワークフローを作成する

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: ディレクトリを作成する**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: `release.yml` を作成する**

`.github/workflows/release.yml` を以下の内容で作成する:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build:
    runs-on: macos-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5

      - name: 依存パッケージをインストールする
        run: uv sync --group dev

      - name: アプリをビルドする
        run: uv run task build

      - name: create-dmg をインストールする
        run: brew install create-dmg

      - name: DMG を作成する
        run: |
          VERSION="${{ github.ref_name }}"
          create-dmg \
            --volname "Git Lanes" \
            "GitLanes-${VERSION}.dmg" \
            "dist/Git Lanes.app"

      - name: GitHub Release を作成して DMG を添付する
        uses: softprops/action-gh-release@v2
        with:
          files: GitLanes-${{ github.ref_name }}.dmg
```

- [ ] **Step 3: YAML 構文を検証する**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" && echo "YAML OK"
```

期待出力: `YAML OK`

- [ ] **Step 4: コミットする**

```bash
git add .github/workflows/release.yml
git commit -m "chore: GitHub Actions リリースワークフローを追加する"
```

---

### Task 2: bump-my-version の設定を追加する

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 現在の `pyproject.toml` のバージョン文字列を確認する**

```bash
grep -n 'version' pyproject.toml git_lanes.spec
```

期待出力（抜粋）:
```
pyproject.toml:3:version = "0.1.0"
git_lanes.spec:79:    "CFBundleShortVersionString": "0.1.0",
```

- [ ] **Step 2: `pyproject.toml` に bump-my-version 設定を追加する**

`pyproject.toml` の末尾に以下を追記する:

```toml
[tool.bumpversion]
current_version = "0.1.0"
commit = true
tag = true
tag_name = "v{new_version}"

[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'

[[tool.bumpversion.files]]
filename = "git_lanes.spec"
search = '"CFBundleShortVersionString": "{current_version}"'
replace = '"CFBundleShortVersionString": "{new_version}"'
```

- [ ] **Step 3: ドライランで動作確認する**

```bash
uvx bump-my-version bump patch --dry-run --verbose
```

期待出力（抜粋）:
```
Would change version 0.1.0 to 0.1.1
  pyproject.toml: version = "0.1.0" -> version = "0.1.1"
  git_lanes.spec: "CFBundleShortVersionString": "0.1.0" -> "CFBundleShortVersionString": "0.1.1"
```

- [ ] **Step 4: コミットする**

```bash
git add pyproject.toml
git commit -m "chore: bump-my-version の設定を追加する"
```

---

### Task 3: README.md にリリース手順を追記する

**Files:**
- Modify: `README.md`

- [ ] **Step 1: `README.md` の「ライセンス」セクションの直前にリリース手順を追記する**

`## ライセンス` の直前に以下を挿入する:

```markdown
## リリース手順

```bash
uvx bump-my-version bump patch   # patch バージョンを上げる（minor / major も同様）
git push && git push --tags      # GitHub Actions が発火して DMG 付き Release を作成
```

バージョン番号の種類:

| コマンド | 変更例 |
|---|---|
| `bump patch` | `0.1.0` → `0.1.1` |
| `bump minor` | `0.1.0` → `0.2.0` |
| `bump major` | `0.1.0` → `1.0.0` |

```

- [ ] **Step 2: Markdown Lint を実行して問題がないか確認する**

```bash
uv run task lint:md
```

期待出力: エラーなし（ゼロ exit code）

- [ ] **Step 3: コミットする**

```bash
git add README.md
git commit -m "docs: README にリリース手順を追記する"
```
