"""branch_filter モジュールのテスト。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.branch_filter import categorize_branches


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
