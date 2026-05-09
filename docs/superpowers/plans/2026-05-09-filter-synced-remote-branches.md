# 同期済みリモートブランチ非表示化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ローカルブランチと同じ先端コミットを持つリモートトラッキングブランチをグラフから除外する。乖離している場合は両方表示する。

**Architecture:** DB には全ブランチを保存したまま、表示層（`graph_service.sync_and_build()`）でフィルタを適用する。新モジュール `backend/services/branch_filter.py` にフィルタ関数を定義し、`graph_service.py` でブランチ取得直後に呼び出す。

**Tech Stack:** Python 3.12+, SQLModel, pygit2, pytest

---

## ファイル構成

| ファイル | 種別 | 役割 |
|---|---|---|
| `backend/services/branch_filter.py` | 新規 | `filter_synced_remote_branches()` を定義 |
| `backend/services/graph_service.py` | 修正 | ブランチ取得後にフィルタを適用 |
| `tests/unit/test_branch_filter.py` | 新規 | フィルタ関数の単体テスト |

---

### Task 1: `filter_synced_remote_branches` のテストを書く

**Files:**
- Create: `tests/unit/test_branch_filter.py`

- [ ] **Step 1: テストファイルを作成する**

`tests/unit/test_branch_filter.py` を以下の内容で作成する:

```python
"""branch_filter モジュールのテスト。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.branch_filter import filter_synced_remote_branches


def _local(name: str, tip: str) -> Branch:
    return Branch(name=name, repo_id="repo1", tip_hash=tip, is_remote=0)


def _remote(name: str, tip: str) -> Branch:
    return Branch(name=name, repo_id="repo1", tip_hash=tip, is_remote=1)


def test_同名ローカルと同じtipのリモートブランチが除外される():
    # --- Arrange ---
    branches = [
        _local("main", "abc123"),
        _remote("origin/main", "abc123"),
    ]

    # --- Act ---
    result = filter_synced_remote_branches(branches)

    # --- Assert ---
    names = [b.name for b in result]
    assert "main" in names
    assert "origin/main" not in names


def test_同名ローカルと異なるtipのリモートブランチは残る():
    # --- Arrange ---
    branches = [
        _local("main", "abc123"),
        _remote("origin/main", "xyz789"),
    ]

    # --- Act ---
    result = filter_synced_remote_branches(branches)

    # --- Assert ---
    names = [b.name for b in result]
    assert "main" in names
    assert "origin/main" in names


def test_対応するローカルブランチがないリモートブランチは残る():
    # --- Arrange ---
    branches = [
        _local("main", "abc123"),
        _remote("origin/feature", "def456"),
    ]

    # --- Act ---
    result = filter_synced_remote_branches(branches)

    # --- Assert ---
    names = [b.name for b in result]
    assert "origin/feature" in names


def test_複数リモートが混在する場合でも正しくフィルタされる():
    # --- Arrange ---
    # origin/main は同期済み → 除外
    # upstream/main は同期済み → 除外
    # origin/feature は乖離 → 残す
    branches = [
        _local("main", "abc123"),
        _remote("origin/main", "abc123"),
        _remote("upstream/main", "abc123"),
        _remote("origin/feature", "zzz999"),
    ]

    # --- Act ---
    result = filter_synced_remote_branches(branches)

    # --- Assert ---
    names = [b.name for b in result]
    assert "main" in names
    assert "origin/main" not in names
    assert "upstream/main" not in names
    assert "origin/feature" in names


def test_スラッシュを含むブランチ名でも正しくフィルタされる():
    # --- Arrange ---
    branches = [
        _local("feature/abc", "abc123"),
        _remote("origin/feature/abc", "abc123"),
    ]

    # --- Act ---
    result = filter_synced_remote_branches(branches)

    # --- Assert ---
    names = [b.name for b in result]
    assert "feature/abc" in names
    assert "origin/feature/abc" not in names


def test_ローカルブランチのみの場合は変更なし():
    # --- Arrange ---
    branches = [
        _local("main", "abc123"),
        _local("feature", "def456"),
    ]

    # --- Act ---
    result = filter_synced_remote_branches(branches)

    # --- Assert ---
    assert result == branches


def test_空リストは空リストを返す():
    # --- Arrange ---
    branches: list[Branch] = []

    # --- Act ---
    result = filter_synced_remote_branches(branches)

    # --- Assert ---
    assert result == []
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
uv run pytest tests/unit/test_branch_filter.py -v
```

期待結果: `ModuleNotFoundError: No module named 'backend.services.branch_filter'`

---

### Task 2: `filter_synced_remote_branches` を実装する

**Files:**
- Create: `backend/services/branch_filter.py`

- [ ] **Step 3: モジュールを作成する**

`backend/services/branch_filter.py` を以下の内容で作成する:

```python
"""リモートトラッキングブランチのフィルタリング。"""

from __future__ import annotations

from backend.models import Branch


def filter_synced_remote_branches(branches: list[Branch]) -> list[Branch]:
    """同期済みリモートブランチを除外する。

    ローカルブランチと同じ先端コミットを持つリモートブランチを除外する。
    乖離している場合（tip が異なる場合）はリモートブランチを残す。

    Args:
        branches: ローカル・リモート混在のブランチリスト。

    Returns:
        同期済みリモートブランチを除いたリスト。
    """
    local_tips = {b.name: b.tip_hash for b in branches if b.is_remote == 0}
    return [b for b in branches if not _is_synced_remote(b, local_tips)]


def _is_synced_remote(branch: Branch, local_tips: dict[str, str]) -> bool:
    """ローカルと同期済みのリモートブランチかどうかを判定する。

    Args:
        branch: 判定対象のブランチ。
        local_tips: ローカルブランチ名 → tip_hash のマップ。

    Returns:
        除外すべき同期済みリモートブランチなら True。
    """
    if branch.is_remote == 0:
        return False
    short_name = branch.name.split("/", 1)[1] if "/" in branch.name else branch.name
    return local_tips.get(short_name) == branch.tip_hash
```

- [ ] **Step 4: テストを実行して全件パスを確認する**

```bash
uv run pytest tests/unit/test_branch_filter.py -v
```

期待結果: 7 件すべて PASSED

- [ ] **Step 5: コミットする**

```bash
git add backend/services/branch_filter.py tests/unit/test_branch_filter.py
git commit -m "feat: 同期済みリモートブランチを除外するフィルタを追加する"
```

---

### Task 3: `graph_service.py` にフィルタを組み込む

**Files:**
- Modify: `backend/services/graph_service.py`

- [ ] **Step 6: `graph_service.py` を修正する**

`backend/services/graph_service.py` の `sync_and_build()` 関数を以下のように変更する:

変更前（39行目付近）:
```python
    branches = branch_repo.list_branches(session, repo_id)
    tags = tag_repo.list_tags(session, repo_id)
```

変更後:
```python
    from backend.services.branch_filter import filter_synced_remote_branches

    branches = filter_synced_remote_branches(branch_repo.list_branches(session, repo_id))
    tags = tag_repo.list_tags(session, repo_id)
```

ファイル冒頭の import ブロックにまとめて追記しても良い。その場合は以下を追加する:

```python
from backend.services.branch_filter import filter_synced_remote_branches
```

そして `sync_and_build()` 内の該当行を:

```python
    branches = filter_synced_remote_branches(branch_repo.list_branches(session, repo_id))
```

に変更する。

- [ ] **Step 7: 既存の全テストが通ることを確認する**

```bash
uv run pytest tests/unit/ -v
```

期待結果: 全件 PASSED（新規 7 件 + 既存テスト）

- [ ] **Step 8: lint と型チェックを通す**

```bash
uv run task lint && uv run task typecheck
```

期待結果: エラーなし

- [ ] **Step 9: コミットする**

```bash
git add backend/services/graph_service.py
git commit -m "feat: graph_service でリモートブランチフィルタを適用する"
```
