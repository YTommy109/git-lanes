# backend/services/grid_builder_utils.py
"""グリッドグラフエンジンの補助関数群（コミット配置用）。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.grid_models import GRID_COLORS, GridBranchLabel, GridLayout, GridNode


def _reserve_secondary_parents(
    commit_hash: str,
    commit_parents: list[str],
    placed: dict[str, GridNode],
    used_lane_nums: set[int],
    active_lanes: list[tuple[int, str, str, str]],
    color_idx: int,
) -> tuple[list[tuple[int, str, str, str]], set[int], int]:
    """第2親以降のレーンを予約して active_lanes に追加する。"""
    from backend.services.grid_builder_helpers import next_available_lane

    for p2_hash in commit_parents[1:]:
        if p2_hash in placed:
            continue
        p2_lane = next_available_lane(used_lane_nums)
        p2_color = GRID_COLORS[color_idx % len(GRID_COLORS)]
        color_idx += 1
        used_lane_nums.add(p2_lane)
        active_lanes.append((p2_lane, commit_hash, p2_hash, p2_color))
    return active_lanes, used_lane_nums, color_idx


_ActiveLanes = list[tuple[int, str, str, str]]
_PlacedMap = dict[str, GridNode]
_CommitState = tuple[_PlacedMap, _ActiveLanes, set[int], int]


def _process_one_commit(
    commit_hash: str,
    row: int,
    placed: _PlacedMap,
    active_lanes: _ActiveLanes,
    used_lane_nums: set[int],
    tip_lane: dict[str, int],
    tip_color: dict[str, str],
    color_idx: int,
    commit_parents: list[str],
    layout: GridLayout,
) -> _CommitState:
    """1コミットをグリッドに配置し状態を更新する。"""
    from backend.services.grid_builder_helpers import (
        assign_commit_lane,
        find_matched_idx,
        update_active_lanes,
    )

    matched_idx = find_matched_idx(commit_hash, active_lanes)
    lane, color, color_idx = assign_commit_lane(
        commit_hash,
        matched_idx,
        active_lanes,
        tip_lane,
        tip_color,
        used_lane_nums,
        color_idx,
    )
    used_lane_nums.add(lane)
    active_lanes, used_lane_nums, color_idx = update_active_lanes(
        commit_hash,
        commit_parents,
        matched_idx,
        lane,
        color,
        active_lanes,
        used_lane_nums,
        color_idx,
        placed,
    )
    node = GridNode(hash=commit_hash, lane=lane, row=row, kind="commit", color=color)
    placed[commit_hash] = node
    layout.nodes.append(node)
    return placed, active_lanes, used_lane_nums, color_idx


def _build_branch_labels(
    branches: list[Branch],
    tip_lane: dict[str, int],
    color_map: dict[str, str],
    placed: dict[str, GridNode],
) -> list[GridBranchLabel]:
    """ブランチラベルリストを構築する。

    Args:
        branches: ブランチのリスト。
        tip_lane: ブランチ tip からレーン番号へのマップ。
        color_map: ブランチ名から色へのマップ。
        placed: 配置済みコミットのマップ。

    Returns:
        GridBranchLabel のリスト。
    """
    lane_to_names: dict[int, list[str]] = {}
    lane_to_color: dict[int, str] = {}
    for b in branches:
        tip_h = b.tip_hash
        target_lane = placed[tip_h].lane if tip_h in placed else tip_lane.get(tip_h)
        if target_lane is None:
            continue
        lane_to_names.setdefault(target_lane, []).append(b.name)
        lane_to_color[target_lane] = color_map.get(b.name, GRID_COLORS[0])
    return [
        GridBranchLabel(lane=ln, names=names, color=lane_to_color[ln])
        for ln, names in lane_to_names.items()
    ]
