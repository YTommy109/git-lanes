# backend/services/grid_builder_utils.py
"""グリッドグラフエンジンの補助関数群（コミット配置用）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.services.grid_builder_helpers import (
    assign_commit_lane,
    find_matched_idx,
    next_available_lane,
)
from backend.services.grid_models import GRID_COLORS, GridLayout, GridNode


def _reserve_secondary_parents(
    commit_hash: str,
    commit_parents: list[str],
    placed: dict[str, GridNode],
    used_lane_nums: set[int],
    active_lanes: list[tuple[int, str, str, str]],
    color_idx: int,
) -> tuple[list[tuple[int, str, str, str]], set[int], int]:
    """第2親以降のレーンを予約して active_lanes に追加する。"""
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


@dataclass
class CommitState:
    """build_layout の可変状態を保持するデータクラス。"""

    placed: _PlacedMap = field(default_factory=dict)
    active_lanes: _ActiveLanes = field(default_factory=list)
    used_lane_nums: set[int] = field(default_factory=set)
    color_idx: int = 0


def _resolve_lane(
    commit_hash: str,
    state: CommitState,
    tip_lane: dict[str, int],
    tip_color: dict[str, str],
) -> tuple[int, str, int | None]:
    """レーン・色・matched_idx を決定し state.color_idx を更新する。"""
    matched_idx = find_matched_idx(commit_hash, state.active_lanes)
    lane, color, state.color_idx = assign_commit_lane(
        commit_hash,
        matched_idx,
        state.active_lanes,
        tip_lane,
        tip_color,
        state.used_lane_nums,
        state.color_idx,
    )
    return lane, color, matched_idx


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
    p1 = commit_parents[0] if commit_parents else None
    new_active: list[tuple[int, str, str, str]] = []
    freed: set[int] = set()
    matched_consumed = False
    for i, (ln, bh, eh, color) in enumerate(active_lanes):
        if i == matched_idx:
            matched_consumed = True
            if p1:
                new_active.append((matched_lane, commit_hash, p1, matched_color))
        elif eh == commit_hash:
            # 同コミットを期待していた合流レーンを解放して再利用可能にする
            freed.add(ln)
        else:
            new_active.append((ln, bh, eh, color))
    if not matched_consumed and p1:
        new_active.append((matched_lane, commit_hash, p1, matched_color))
    return _reserve_secondary_parents(
        commit_hash, commit_parents, placed, used_lane_nums - freed, new_active, color_idx
    )


def _process_one_commit(
    commit_hash: str,
    row: int,
    state: CommitState,
    tip_lane: dict[str, int],
    tip_color: dict[str, str],
    commit_parents: list[str],
    layout: GridLayout,
) -> None:
    """1コミットをグリッドに配置し state を更新する。"""
    lane, color, matched_idx = _resolve_lane(commit_hash, state, tip_lane, tip_color)
    state.used_lane_nums.add(lane)
    state.active_lanes, state.used_lane_nums, state.color_idx = update_active_lanes(
        commit_hash,
        commit_parents,
        matched_idx,
        lane,
        color,
        state.active_lanes,
        state.used_lane_nums,
        state.color_idx,
        state.placed,
    )
    node = GridNode(hash=commit_hash, lane=lane, row=row, kind="commit", color=color)
    state.placed[commit_hash] = node
    layout.nodes.append(node)
