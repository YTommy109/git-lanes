"""graph_layout の単体テスト。"""

from backend.models import Branch, Commit
from backend.services.graph_layout import (
    LANE_COLORS,
    BranchLane,
    build_multi_lane_layout,
    build_single_lane_layout,
)

_REPO_ID = "test-repo"


def test_build_single_lane_layout_builds_edges_within_visible_set():
    # --- Arrange ---
    rows = [
        Commit(
            hash="b" * 40,
            short_hash="bbbbbbb",
            message="two",
            author_name="a",
            author_email="a@b.c",
            committed_at=2,
            repo_id=_REPO_ID,
        ),
        Commit(
            hash="a" * 40,
            short_hash="aaaaaaa",
            message="one",
            author_name="a",
            author_email="a@b.c",
            committed_at=1,
            repo_id=_REPO_ID,
        ),
    ]
    parents = {rows[0].hash: [rows[1].hash]}

    # --- Act ---
    nodes, edges = build_single_lane_layout(rows, parents)

    # --- Assert ---
    assert len(nodes) == 2
    assert len(edges) == 1
    assert edges[0].child_hash == rows[0].hash
    assert edges[0].parent_hash == rows[1].hash


def _make_commit(hash_prefix: str, at: int) -> Commit:
    """テスト用 Commit を生成する。"""
    h = hash_prefix * 40
    return Commit(
        hash=h,
        short_hash=h[:7],
        message="msg",
        author_name="a",
        author_email="a@b.c",
        committed_at=at,
        repo_id=_REPO_ID,
    )


def _make_branch(name: str, tip_prefix: str) -> Branch:
    """テスト用 Branch を生成する。"""
    return Branch(name=name, repo_id=_REPO_ID, tip_hash=tip_prefix * 40, is_remote=0)


def test_LANE_COLORS_は8色():
    assert len(LANE_COLORS) == 8


def test_BranchLane_は必須フィールドを持つ():
    # --- Arrange / Act ---
    bl = BranchLane(
        name="main",
        lane=0,
        tip_hash="a" * 40,
        has_unique_commits=True,
        connect_hash="a" * 40,
        x=36.0,
    )

    # --- Assert ---
    assert bl.lane == 0
    assert bl.x == 36.0


def test_build_multi_lane_layout_mainのみのリポジトリ():
    # --- Arrange ---
    rows = [_make_commit("b", 2), _make_commit("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_make_branch("main", "b")]

    # --- Act ---
    nodes, edges, branch_lanes = build_multi_lane_layout(rows, parents, branches)

    # --- Assert ---
    assert len(nodes) == 2
    assert len(edges) == 1
    assert len(branch_lanes) == 1
    assert branch_lanes[0].lane == 0
    assert all(n.lane == 0 for n in nodes)


def test_build_multi_lane_layout_ブランチ接続点ソートでレーン割り当て():
    # --- Arrange ---
    # main: c(row0) → b(row1) → a(row2)
    # feat/x tip=x → 接続 b(row1)  → lane=1
    # feat/y tip=y → 接続 a(row2)  → lane=2
    rows = [_make_commit("c", 3), _make_commit("b", 2), _make_commit("a", 1)]
    parents = {
        "c" * 40: ["b" * 40],
        "b" * 40: ["a" * 40],
        "x" * 40: ["b" * 40],
        "y" * 40: ["a" * 40],
    }
    branches = [
        _make_branch("main", "c"),
        _make_branch("feat/x", "x"),
        _make_branch("feat/y", "y"),
    ]

    # --- Act ---
    nodes, edges, branch_lanes = build_multi_lane_layout(rows, parents, branches)

    # --- Assert ---
    lane_map = {bl.name: bl.lane for bl in branch_lanes}
    assert lane_map["main"] == 0
    assert lane_map["feat/x"] == 1
    assert lane_map["feat/y"] == 2


def test_build_multi_lane_layout_空データは空を返す():
    # --- Act ---
    nodes, edges, branch_lanes = build_multi_lane_layout([], {}, [])

    # --- Assert ---
    assert nodes == []
    assert edges == []
    assert branch_lanes == []
