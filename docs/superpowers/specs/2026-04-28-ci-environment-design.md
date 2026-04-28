# CI 環境設計

**日付:** 2026-04-28
**ブランチ:** chore/ci_env

## 目的

現状は `release.yml` のみで、PR マージ前・main push 時に何のチェックも走らない。
リリース前に品質ゲートを設けることで、壊れたコードが main に入らない・リリースされない状態を作る。

## トリガー

| イベント | ワークフロー |
|---|---|
| PR → main | `ci.yml`（全ジョブ） |
| push → main | `ci.yml`（全ジョブ） |
| タグ push（`v*.*.*`） | `release.yml`（ビルド・リリースのみ） |

## CI ワークフロー（`ci.yml`）

### パイプライン構造

```
lint-typecheck (ubuntu-latest)
  ├─ ruff check .
  └─ ty check

       ↓ pass したら並列起動

test (ubuntu-latest)          test-e2e (ubuntu-latest)
  ├─ pytest tests/unit           ├─ playwright install --with-deps chromium
  ├─ pytest tests/integration    └─ pytest tests/e2e -v
  └─ coverage ≥ 85%
```

### ジョブ詳細

**`lint-typecheck`**
- ランナー: `ubuntu-latest`
- `ruff check .` → `ty check`
- 失敗時: `test` / `test-e2e` は起動しない

**`test`**
- ランナー: `ubuntu-latest`
- `needs: lint-typecheck`
- `pytest tests/unit tests/integration -v --cov --cov-report=term-missing`
- カバレッジ 85% 未満で失敗（`pyproject.toml` の `fail_under = 85` を適用）

**`test-e2e`**
- ランナー: `ubuntu-latest`
- `needs: lint-typecheck`
- `playwright install --with-deps chromium` でブラウザをインストール
- `pytest tests/e2e -v`
- E2E conftest が FastAPI サーバーをサブプロセスで自動起動するため追加設定不要

## リリースワークフロー（`release.yml`）変更点

- `actions/checkout@v6`（存在しないバージョン）→ `v4` に修正
- CI ロジックは追加しない（branch protection で main の品質が保証されるため）

## ブランチ保護設定（GitHub 画面で一度だけ設定）

Settings → Branches → Add rule → `main`

| 項目 | 設定値 |
|---|---|
| Require status checks to pass before merging | ✅ |
| Required status checks | `lint-typecheck` / `test` / `test-e2e` |
| Require branches to be up to date before merging | ✅ |
| Do not allow bypassing the above settings | ✅ |

設定手順の詳細は `docs/github-branch-protection.md` に記載する。

## 保護フロー全体像

```
開発者 → PR 作成
  └─ CI: lint-typecheck → test + test-e2e
       └─ 全 pass → マージ可能
              ↓
           main（常に緑）
              ↓
         タグ push → release.yml → ビルド → DMG → GitHub Release
```

## 対象外（スコープ外）

- Windows / macOS ランナーでのテスト（Python 3.12 固定のため不要）
- 複数 Python バージョンのマトリクステスト
- キャッシュ戦略の最適化（初期実装では省略）
