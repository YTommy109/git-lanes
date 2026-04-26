"""コミットグラフの単純レイアウト（単レーン）。"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models import Branch, Commit
from backend.services.topo_sort import topological_sort


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
class EdgeSegment:
    """SVG に描画する線分。"""

    x1: float
    y1: float
    x2: float
    y2: float
    lane: int


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
    """コミット列にトポロジカル順で縦方向の座標を割り当てる。"""
    sorted_rows = topological_sort(rows, parents)
    visible = {r.hash for r in rows}
    nodes = [LayoutNode(commit=r, x=56.0, y=36.0 + i * 52.0) for i, r in enumerate(sorted_rows)]
    edges: list[LayoutEdge] = []
    for r in sorted_rows:
        for ph in parents.get(r.hash, []):
            if ph in visible:
                edges.append(LayoutEdge(child_hash=r.hash, parent_hash=ph))
    return nodes, edges


def _chain_length(tip_hash: str, parents: dict[str, list[str]], row_set: set[str]) -> int:
    """第1親チェーンの可視コミット数を返す。"""
    count, current = 0, tip_hash
    while current and current in row_set:
        count += 1
        chain = parents.get(current, [])
        current = chain[0] if chain else None
    return count


def build_multi_lane_layout(
    rows: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
) -> tuple[list[LayoutNode], list[LayoutEdge], list[BranchLane]]:
    """GitUp スタイルのマルチレーンレイアウトを計算する。"""
    from backend.services.lane_assignment import (  # noqa: PLC0415
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
    main_branch = max(
        branches,
        key=lambda b: (
            _chain_length(b.tip_hash, parents, row_set),
            1 if b.name in {"main", "master"} else 0,
        ),
    )
    main_hashes = _find_main_hashes(main_branch.tip_hash, parents, row_set)
    branch_lanes = _assign_lanes(
        branches, main_branch, parents, main_hashes, row_set, hash_to_row, rows
    )
    tip = main_branch.tip_hash
    main_lane = BranchLane(main_branch.name, 0, tip, True, tip, LANE_OFFSET)
    all_lanes = [main_lane] + branch_lanes
    hash_to_lane = _build_hash_to_lane(branch_lanes, parents, main_hashes, row_set)
    nodes = build_lane_nodes(rows, hash_to_lane)
    edges = build_lane_edges(rows, parents, row_set)
    return nodes, edges, all_lanes


def build_edge_segments(
    nodes: list[LayoutNode],
    edges: list[LayoutEdge],
) -> list[EdgeSegment]:
    """LayoutEdge を EdgeSegment リストに変換する。異レーンは縦線+斜め線2本に分割。"""
    node_map = {n.commit.hash: n for n in nodes}
    segments: list[EdgeSegment] = []
    for e in edges:
        c, p = node_map[e.child_hash], node_map[e.parent_hash]
        if c.x == p.x:
            segments.append(EdgeSegment(c.x, c.y, p.x, p.y, c.lane))
        else:
            bend_y = p.y - ROW_SPACING
            segments.append(EdgeSegment(c.x, c.y, c.x, bend_y, c.lane))
            segments.append(EdgeSegment(c.x, bend_y, p.x, p.y, c.lane))
    return segments
