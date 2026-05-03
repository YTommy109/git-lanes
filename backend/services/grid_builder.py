# backend/services/grid_builder.py
"""グリッドグラフエンジン。"""

from __future__ import annotations

from itertools import groupby

from backend.models import Branch, Commit, Tag
from backend.services.graph_models import GraphResult
from backend.services.grid_builder_helpers import (
    add_joint_edges,
    assign_commit_lane,
    build_dummy_nodes,
    find_matched_idx,
    init_branch_maps,
    update_active_lanes,
)
from backend.services.grid_models import (
    GRID_COLORS,
    GridBranchLabel,
    GridEdge,
    GridLayout,
    GridNode,
)


def _place_commits(
    sorted_commits: list[Commit],
    parents: dict[str, list[str]],
    tip_lane: dict[str, int],
    tip_color: dict[str, str],
    used_lane_nums: set[int],
    layout: GridLayout,
) -> dict[str, GridNode]:
    """コミットをグリッドに配置し placed マップを返す。"""
    placed: dict[str, GridNode] = {}
    row = 0
    active_lanes: list[tuple[int, str, str, str]] = []
    color_idx = len(used_lane_nums)

    for _, group in groupby(sorted_commits, key=lambda c: c.committed_at):
        for commit in list(group):
            h = commit.hash
            commit_parents = parents.get(h, [])
            matched_idx = find_matched_idx(h, active_lanes)
            matched_lane, matched_color, color_idx = assign_commit_lane(
                h,
                matched_idx,
                active_lanes,
                tip_lane,
                tip_color,
                used_lane_nums,
                color_idx,
            )
            used_lane_nums.add(matched_lane)
            active_lanes, used_lane_nums, color_idx = update_active_lanes(
                h,
                commit_parents,
                matched_idx,
                matched_lane,
                matched_color,
                active_lanes,
                used_lane_nums,
                color_idx,
                placed,
            )
            node = GridNode(hash=h, lane=matched_lane, row=row, kind="commit", color=matched_color)
            placed[h] = node
            layout.nodes.append(node)
        row += 1

    return placed


def _add_commit_edges(
    layout: GridLayout,
    parents: dict[str, list[str]],
    placed: dict[str, GridNode],
) -> None:
    """各コミットから親へのエッジを生成する。"""
    for node in layout.nodes:
        if node.kind != "commit":
            continue
        for p_hash in parents.get(node.hash or "", []):
            if p_hash not in placed:
                continue
            p_node = placed[p_hash]
            if node.lane == p_node.lane or abs(p_node.row - node.row) == 1:
                layout.edges.append(
                    GridEdge(
                        from_lane=node.lane,
                        from_row=node.row,
                        to_lane=p_node.lane,
                        to_row=p_node.row,
                        color=node.color,
                        dashed=False,
                    )
                )
            else:
                add_joint_edges(layout, node, p_node)


def build_layout(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GridLayout:
    """グリッドレイアウトを計算する。"""
    tip_lane, color_map, tip_color = init_branch_maps(branches)
    layout = GridLayout()
    sorted_commits = sorted(commits, key=lambda c: -c.committed_at)
    placed = _place_commits(
        sorted_commits,
        parents,
        tip_lane,
        tip_color,
        set(tip_lane.values()),
        layout,
    )

    build_dummy_nodes(layout, branches, tip_lane, color_map, placed)
    _add_commit_edges(layout, parents, placed)
    lane_to_names: dict[int, list[str]] = {}
    lane_to_color: dict[int, str] = {}
    for b in branches:
        tip_h = b.tip_hash
        target_lane = placed[tip_h].lane if tip_h in placed else tip_lane.get(tip_h)
        if target_lane is None:
            continue
        lane_to_names.setdefault(target_lane, []).append(b.name)
        lane_to_color[target_lane] = color_map.get(b.name, GRID_COLORS[0])
    for ln, names in lane_to_names.items():
        layout.branch_labels.append(GridBranchLabel(lane=ln, names=names, color=lane_to_color[ln]))

    return layout


def build_grid(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GraphResult:
    """グリッドエンジンでグラフを構築して GraphResult を返す。"""
    from backend.services.grid_coords import to_svg

    layout = build_layout(commits, parents, branches, tags, head_hash)
    return to_svg(layout)
