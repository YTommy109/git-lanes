"""branch_filter モジュールのテスト。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.branch_filter import (
    categorize_branches,
    filter_synced_remote_branches,
)


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


def test_categorize_branches_ローカルブランチのみの場合はlocalに全て入る():
    # --- Arrange ---
    branches = [
        Branch(name="main", repo_id="r", tip_hash="aaa", is_remote=0),
        Branch(name="feat", repo_id="r", tip_hash="bbb", is_remote=0),
    ]

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert len(cats.local) == 2
    assert cats.synced_remotes == []
    assert cats.diverged_remotes == []


def test_categorize_branches_tipが一致するリモートがsynced_remotesに入る():
    # --- Arrange ---
    branches = [
        Branch(name="main", repo_id="r", tip_hash="aaa", is_remote=0),
        Branch(name="origin/main", repo_id="r", tip_hash="aaa", is_remote=1),
    ]

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert len(cats.synced_remotes) == 1
    assert cats.synced_remotes[0].name == "origin/main"
    assert cats.diverged_remotes == []


def test_categorize_branches_名前が違ってもtipが一致すればsynced_remotesに入る():
    # origin/HEAD のように名前が異なるケースでも tip 一致で分類される
    # --- Arrange ---
    branches = [
        Branch(name="main", repo_id="r", tip_hash="aaa", is_remote=0),
        Branch(name="origin/HEAD", repo_id="r", tip_hash="aaa", is_remote=1),
    ]

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert len(cats.synced_remotes) == 1
    assert cats.synced_remotes[0].name == "origin/HEAD"


def test_categorize_branches_tipが異なるリモートがdiverged_remotesに入る():
    # --- Arrange ---
    branches = [
        Branch(name="main", repo_id="r", tip_hash="aaa", is_remote=0),
        Branch(name="origin/main", repo_id="r", tip_hash="bbb", is_remote=1),
    ]

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert cats.synced_remotes == []
    assert len(cats.diverged_remotes) == 1
    assert cats.diverged_remotes[0].name == "origin/main"


def test_categorize_branches_空リストは空カテゴリを返す():
    # --- Arrange ---
    branches: list[Branch] = []

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert cats.local == []
    assert cats.synced_remotes == []
    assert cats.diverged_remotes == []
