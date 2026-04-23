---
name: test-write
description: Git Lanes プロジェクトのテストを書く。単体テストは AAA スタイル（pytest・日本語コメント）、E2E テストはガーキン記法（Playwright・日本語コメント）で記述する。
type: rigid
---

# Git Lanes テスト作成スキル

## 単体テスト（pytest）

### 配置場所

```
tests/unit/<対象モジュール名>/test_<対象ファイル名>.py
```

### テンプレート

```python
"""<モジュール名> の単体テスト。"""

import pytest
from git_lanes.<module> import <TargetClass>


class Test<TargetClass>:
    """<TargetClass> のテストスイート。"""

    def test_<状態>_<操作>_<期待結果>(self):
        """<テストの意図を日本語で一行説明>。"""
        # --- Arrange ---
        # テストに必要なデータや依存物を準備する

        # --- Act ---
        # テスト対象の処理を1回だけ呼び出す

        # --- Assert ---
        # 期待する結果を検証する
```

### テスト名の命名規則

```
test_<前提条件>_<操作>_<期待結果>
```

例:
- `test_valid_hash_parse_returns_short_hash`
- `test_empty_repo_get_commits_returns_empty_list`
- `test_invalid_path_create_repository_raises_error`

### モックの使い方

外部依存（pygit2・SQLite・watchdog）はモックする。ビジネスロジックはモックしない。

```python
from unittest.mock import MagicMock, patch


def test_head_changed_sync_updates_cache():
    # --- Arrange ---
    # pygit2 のリポジトリをモックする
    mock_repo = MagicMock()
    mock_repo.head.target = "newhead123"

    # --- Act ---
    with patch("git_lanes.repositories.git_repo.pygit2.Repository", return_value=mock_repo):
        result = sync_service.sync("repo-id-1")

    # --- Assert ---
    assert result.updated_count > 0
```

### カバレッジの考え方

- 正常系・異常系・境界値をカバーする
- 「とりあえず呼ぶだけ」のテストは書かない
- カバレッジ 85〜90% を目指すが、意味のないケースは追加しない

## E2E テスト（Playwright・TypeScript）

### 配置場所

```
tests/e2e/<機能名>.spec.ts
```

### テンプレート

```typescript
import { test, expect } from "@playwright/test";

test.describe("<機能名>", () => {
    test("<テストの目的を日本語で説明>", async ({ page }) => {
        // Given: <前提条件を日本語で説明>
        await page.goto("/");
        await page.waitForSelector(".commit-node");

        // When: <操作を日本語で説明>
        await page.locator("<selector>").click();

        // Then: <期待結果を日本語で説明>
        await expect(page.locator("<selector>")).toBeVisible();
    });
});
```

### Electron アプリを直接テストする場合

```typescript
import { test, expect, _electron as electron } from "@playwright/test";

test.describe("Electron アプリ起動", () => {
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
});
```

### E2E で重点的にテストすること

| 項目 | テスト方法 |
|------|-----------|
| 画面遷移 | `page.goto()` → セレクタの存在確認 |
| ボタンが動作する | `.click()` → 結果の DOM 変化を確認 |
| メニューの disable/enable | `toBeDisabled()` / `toBeEnabled()` |
| htmx の非同期更新 | `waitForSelector()` で DOM 変化を待つ |

### E2E でテストしないこと

- ビジネスロジックの境界値（単体テストで行う）
- すべてのエラーパターン（ハッピーパスと主要な操作制御に集中）

## テスト作成の手順

1. テスト対象のコードを Read して仕様を把握する
2. テストケースの一覧を列挙してユーザーに確認する
3. テンプレートに沿ってテストを記述する
4. `uv run task test` を実行してグリーンになることを確認する
5. カバレッジレポートを確認して不足があれば追加する
