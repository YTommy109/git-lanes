# backend/services/grid_builder_helpers.py
"""グリッドグラフエンジンのレーン割り当てヘルパー関数群。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.grid_models import GRID_COLORS, GridEdge, GridLayout, GridNode


def _e(
    from_lane: int, from_row: int, to_lane: int, to_row: int, color: str, dashed: bool
) -> GridEdge:
    """GridEdge を生成するショートハンド。"""
    return GridEdge(
        from_lane=from_lane,
        from_row=from_row,
        to_lane=to_lane,
        to_row=to_row,
        color=color,
        dashed=dashed,
    )


def init_branch_maps(
    branches: list[Branch],
) -> tuple[dict[str, int], dict[str, str], dict[str, str]]:
    """ブランチのレーン・色マップを初期化する。

    Args:
        branches: ブランチのリスト。リスト順にレーン番号を割り当てる。

    Returns:
        (tip_lane, color_map, tip_color) のタプル。
    """
    branch_lane: dict[str, int] = {}
    lane_num = 1
    for b in branches:
        if b.name not in branch_lane:
            branch_lane[b.name] = lane_num
            lane_num += 3
    tip_lane: dict[str, int] = {}
    for b in branches:
        if b.tip_hash not in tip_lane:
            tip_lane[b.tip_hash] = branch_lane[b.name]
    color_map: dict[str, str] = {}
    for i, b in enumerate(branches):
        if b.name not in color_map:
            color_map[b.name] = GRID_COLORS[i % len(GRID_COLORS)]
    tip_color: dict[str, str] = {b.tip_hash: color_map[b.name] for b in branches}
    return tip_lane, color_map, tip_color


def next_available_lane(used: set[int]) -> int:
    """未使用の最小レーン番号を返す。"""
    candidate = 1
    while candidate in used:
        candidate += 1
    return candidate


def find_matched_idx(
    commit_hash: str,
    active_lanes: list[tuple[int, str, str, str]],
) -> int | None:
    """commit_hash を期待するエントリのインデックスを返す。見つからない場合は None。

    Args:
        commit_hash: 検索するコミットハッシュ。
        active_lanes: アクティブレーンのリスト。

    Returns:
        一致するインデックス。見つからない場合は None。
    """
    for i, (_, _bh, expected_h, _) in enumerate(active_lanes):
        if commit_hash == expected_h:
            return i
    return None


def assign_commit_lane(
    commit_hash: str,
    matched_idx: int | None,
    active_lanes: list[tuple[int, str, str, str]],
    tip_lane: dict[str, int],
    tip_color: dict[str, str],
    used_lane_nums: set[int],
    color_idx: int,
) -> tuple[int, str, int]:
    """レーンと色を決定する。競合時は小さい方を優先する。

    Returns:
        (lane_num, color, color_idx) のタプル。
    """
    al_num = active_lanes[matched_idx][0] if matched_idx is not None else None
    al_color = active_lanes[matched_idx][3] if matched_idx is not None else None
    tl_num = tip_lane.get(commit_hash)
    tl_color = tip_color.get(commit_hash)
    if al_num is not None and tl_num is not None:
        if tl_num <= al_num:
            return tl_num, tl_color or GRID_COLORS[0], color_idx
        return al_num, al_color or GRID_COLORS[0], color_idx
    if tl_num is not None:
        return tl_num, tl_color or GRID_COLORS[0], color_idx
    if al_num is not None:
        return al_num, al_color or GRID_COLORS[0], color_idx
    ln = next_available_lane(used_lane_nums)
    return ln, GRID_COLORS[color_idx % len(GRID_COLORS)], color_idx + 1


def update_active_lanes(
    commit_hash: str,
    commit_parents: list[str],
    matched_idx: int | None,
    matched_lane: int,
    matched_color: str,
    active_lanes: list[tuple[int, str, str, str]],
    used_lane_nums: set[int],
    color_idx: int,
    placed: dict[str, GridNode],
) -> tuple[list[tuple[int, str, str, str]], set[int], int]:
    """active_lanes を更新し、第2親以降のレーンを予約する。"""
    from backend.services.grid_builder_utils import _reserve_secondary_parents

    p1 = commit_parents[0] if commit_parents else None
    new_active: list[tuple[int, str, str, str]] = []
    matched_consumed = False
    for i, (ln, bh, eh, color) in enumerate(active_lanes):
        if i == matched_idx:
            matched_consumed = True
            if p1:
                new_active.append((matched_lane, commit_hash, p1, matched_color))
        else:
            new_active.append((ln, bh, eh, color))
    if not matched_consumed and p1:
        new_active.append((matched_lane, commit_hash, p1, matched_color))
    return _reserve_secondary_parents(
        commit_hash, commit_parents, placed, used_lane_nums, new_active, color_idx
    )


def add_joint_edges(layout: GridLayout, from_node: GridNode, to_node: GridNode) -> None:
    """複数行のエッジをジョイントで分割する。"""
    c, cr, fc = from_node.lane, from_node.row, from_node.color
    while cr + 1 < to_node.row:
        nr = cr + 1
        layout.nodes.append(GridNode(hash=None, lane=c, row=nr, kind="joint", color=fc))
        layout.edges.append(_e(c, cr, c, nr, fc, False))
        cr = nr
    layout.edges.append(_e(c, cr, to_node.lane, to_node.row, fc, False))
