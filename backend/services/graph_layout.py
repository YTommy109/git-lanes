"""コミットグラフの単純レイアウト（単レーン）。"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models import Branch, Commit


@dataclass(frozen=True)
class LayoutNode:
    """レイアウト済みノード。"""

    commit: Commit
    x: float
    y: float
    lane: int = 0


@dataclass(frozen=True)
class LayoutEdge:
    """表示対象内の親子エッジ。"""

    child_hash: str
    parent_hash: str


LANE_COLORS: list[str] = [
    "#e05555",  # 0: main
    "#e67e22",  # 1
    "#2ecc71",  # 2
    "#3498db",  # 3
    "#9b59b6",  # 4
    "#1abc9c",  # 5
    "#f1c40f",  # 6
    "#e91e63",  # 7
]

LANE_WIDTH = 70.0
LANE_OFFSET = 36.0
ROW_SPACING = 60.0
MARGIN_TOP = 145.0


@dataclass(frozen=True)
class BranchLane:
    """ブランチのレーン情報。"""

    name: str
    lane: int
    tip_hash: str
    has_unique_commits: bool
    connect_hash: str
    x: float


def build_single_lane_layout(
    rows: list[Commit], parents: dict[str, list[str]]
) -> tuple[list[LayoutNode], list[LayoutEdge]]:
    """上から新しい順のコミット列に縦方向の座標を割り当てる。

    Args:
        rows: ``committed_at`` 降順で並んだコミット。
        parents: 子ハッシュをキーとする親ハッシュのリスト。

    Returns:
        ノード一覧と、表示集合内に閉じたエッジ一覧。
    """
    spacing = 52.0
    margin_top = 36.0
    x = 56.0
    visible = {r.hash for r in rows}
    nodes = [LayoutNode(commit=r, x=x, y=margin_top + i * spacing) for i, r in enumerate(rows)]
    edges: list[LayoutEdge] = []
    for r in rows:
        for ph in parents.get(r.hash, []):
            if ph in visible:
                edges.append(LayoutEdge(child_hash=r.hash, parent_hash=ph))
    return nodes, edges


def build_multi_lane_layout(
    rows: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
) -> tuple[list[LayoutNode], list[LayoutEdge], list[BranchLane]]:
    """GitUp スタイルのマルチレーンレイアウトを計算する。

    Args:
        rows: ``committed_at`` 降順で並んだコミット。
        parents: 子ハッシュをキーとする親ハッシュのリスト（position 順）。
        branches: リポジトリの全ブランチ。

    Returns:
        ノード一覧・エッジ一覧・ブランチレーン一覧のタプル。
    """
    from backend.services.lane_assignment import (
        _assign_lanes,
        _build_hash_to_lane,
        _find_main_hashes,
        build_lane_edges,
        build_lane_nodes,
    )

    if not rows or not branches:
        return [], [], []

    row_set = {r.hash for r in rows}
    hash_to_row = {r.hash: i for i, r in enumerate(rows)}
    main_names = {"main", "master"}
    main_branch = next(
        (b for b in branches if b.name in main_names),
        next((b for b in branches if b.tip_hash == rows[0].hash), branches[0]),
    )
    main_hashes = _find_main_hashes(main_branch.tip_hash, parents, row_set)
    branch_lanes = _assign_lanes(
        branches, main_branch, parents, main_hashes, row_set, hash_to_row, rows
    )
    main_lane = BranchLane(
        name=main_branch.name,
        lane=0,
        tip_hash=main_branch.tip_hash,
        has_unique_commits=True,
        connect_hash=main_branch.tip_hash,
        x=LANE_OFFSET,
    )
    all_lanes = [main_lane] + branch_lanes
    hash_to_lane = _build_hash_to_lane(branch_lanes, parents, main_hashes, row_set)
    nodes = build_lane_nodes(rows, hash_to_lane)
    edges = build_lane_edges(rows, parents, row_set)
    return nodes, edges, all_lanes
