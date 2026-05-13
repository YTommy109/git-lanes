# backend/services/grid_builder_helpers.py
"""グリッドグラフエンジンのレーン割り当てヘルパー関数群。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.grid_models import GRID_COLORS, GridEdge, GridLayout, GridNode


def _make_edge(
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
    label_only_branches: list[Branch] | None = None,
) -> tuple[dict[str, int], dict[str, str], dict[str, str]]:
    """ブランチのレーン・色マップを初期化する。

    Args:
        branches: ブランチのリスト。リスト順にレーン番号を割り当てる。
        label_only_branches: レーンを消費せずラベルのみ表示するブランチ。
            color_idx を消費せず、対応する tip のブランチの色を借用する。

    Returns:
        (tip_lane, color_map, tip_color) のタプル。
    """
    branch_lane: dict[str, int] = {}
    tip_lane: dict[str, int] = {}
    color_map: dict[str, str] = {}
    lane_num = 1
    color_idx = 0
    for b in branches:
        if b.name not in branch_lane:
            if b.tip_hash in tip_lane:
                # 同じ tip を持つブランチはレーンを共用し、lane_num を消費しない
                branch_lane[b.name] = tip_lane[b.tip_hash]
            else:
                branch_lane[b.name] = lane_num
                lane_num += 3
            color_map[b.name] = GRID_COLORS[color_idx % len(GRID_COLORS)]
            color_idx += 1
        if b.tip_hash not in tip_lane:
            tip_lane[b.tip_hash] = branch_lane[b.name]
    tip_color: dict[str, str] = {b.tip_hash: color_map[b.name] for b in branches}
    # label_only_branches: color_idx を消費せず既存 tip_color から色を借用する
    for b in label_only_branches or []:
        if b.name not in color_map and b.tip_hash in tip_color:
            color_map[b.name] = tip_color[b.tip_hash]
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


def add_joint_edges(layout: GridLayout, from_node: GridNode, to_node: GridNode) -> None:
    """複数行のエッジをジョイントで分割する。"""
    c, cr, fc = from_node.lane, from_node.row, from_node.color
    while cr + 1 < to_node.row:
        nr = cr + 1
        layout.nodes.append(GridNode(hash=None, lane=c, row=nr, kind="joint", color=fc))
        layout.edges.append(_make_edge(c, cr, c, nr, fc, False))
        cr = nr
    layout.edges.append(_make_edge(c, cr, to_node.lane, to_node.row, fc, False))
