# CI/CD 自動リリース設計

## 概要

タグ `v*.*.*` の push をトリガーに、macOS 向け DMG を自動ビルドして GitHub Release に添付する
GitHub Actions ワークフローを追加する。合わせて bump-my-version によるバージョン管理を整備する。

## スコープ

- `.github/workflows/release.yml` の新規作成
- `pyproject.toml` への bump-my-version 設定追加
- `git_lanes.spec` のバージョン文字列を bump-my-version 管理下に追加
- `README.md` へのリリース手順追記

## ワークフロー設計

### トリガー

```yaml
on:
  push:
    tags:
      - 'v*.*.*'
```

### ジョブ構成

ランナー: `macos-latest`（Apple Silicon M1、Homebrew プリインストール済み）

| ステップ | 詳細 |
|---|---|
| checkout | `actions/checkout@v4` |
| uv セットアップ | `astral-sh/setup-uv@v5` |
| 依存インストール | `uv sync --group dev` |
| ビルド | `uv run task build` → `dist/Git Lanes.app` |
| create-dmg インストール | `brew install create-dmg` |
| DMG 作成 | `GitLanes-{tag}.dmg` を生成 |
| GitHub Release 作成 | `softprops/action-gh-release@v2` で DMG を添付 |

### バージョン抽出

`${{ github.ref_name }}` で取得（例: `v1.2.3`）。DMG ファイル名は `GitLanes-v1.2.3.dmg`。

## bump-my-version 設定

### 管理対象ファイル

| ファイル | 検索パターン |
|---|---|
| `pyproject.toml` | `version = "{current_version}"` |
| `git_lanes.spec` | `"CFBundleShortVersionString": "{current_version}"` |

### 動作

```bash
uvx bump-my-version bump patch   # バージョン更新 + コミット + タグ作成
git push && git push --tags      # CI 発火
```

## コード署名・公証

不要（エンジニア向け配布のため）。

## 前提条件

- パブリックリポジトリのため macOS ランナーは無料枠で使用可能
- リポジトリに `GITHUB_TOKEN` の write 権限が必要（Release 作成のため）
