"""init_branch_maps の label_only_branches パラメータのテスト。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.grid_builder_helpers import init_branch_maps
from backend.services.grid_models import GRID_COLORS


def _local(name: str, tip: str) -> Branch:
    return Branch(name=name, repo_id="r", tip_hash=tip, is_remote=0)


def _remote(name: str, tip: str) -> Branch:
    return Branch(name=name, repo_id="r", tip_hash=tip, is_remote=1)


def test_label_only_branchesはcolor_idxを消費しない():
    # --- Arrange ---
    # label_only が色インデックスに影響しなければ feat は 2番目の色（GRID_COLORS[1]）になる
    main = _local("main", "aaa")
    feat = _local("feat", "bbb")
    origin_main = _remote("origin/main", "aaa")  # main と同じ tip → label_only

    # --- Act ---
    _, color_map, _ = init_branch_maps([main, feat], label_only_branches=[origin_main])

    # --- Assert ---
    assert color_map["main"] == GRID_COLORS[0]
    assert color_map["feat"] == GRID_COLORS[1]  # label_only の影響で GRID_COLORS[2] にならない
    assert color_map["origin/main"] == GRID_COLORS[0]  # main の色を借用


def test_label_only_branchesは既存レーンの色を借用する():
    # --- Arrange ---
    main = _local("main", "aaa")
    origin_main = _remote("origin/main", "aaa")

    # --- Act ---
    _, color_map, _ = init_branch_maps([main], label_only_branches=[origin_main])

    # --- Assert ---
    assert color_map["origin/main"] == color_map["main"]


def test_label_only_branchesがNoneの場合は既存の動作と同じ():
    # --- Arrange ---
    main = _local("main", "aaa")
    feat = _local("feat", "bbb")

    # --- Act ---
    _, color_map_with, _ = init_branch_maps([main, feat], label_only_branches=None)
    _, color_map_without, _ = init_branch_maps([main, feat])

    # --- Assert ---
    assert color_map_with == color_map_without


def test_label_only_branchesのtipがtip_laneにない場合はcolor_mapに追加しない():
    # tip が tip_lane に存在しない label_only は静かに無視される
    # --- Arrange ---
    main = _local("main", "aaa")
    orphan = _remote("origin/orphan", "zzz")  # どのローカルとも一致しない

    # --- Act ---
    _, color_map, _ = init_branch_maps([main], label_only_branches=[orphan])

    # --- Assert ---
    assert "origin/orphan" not in color_map
