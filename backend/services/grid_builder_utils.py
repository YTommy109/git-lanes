# backend/services/grid_builder_utils.py
"""グリッドグラフエンジンの補助関数群（コミット配置用）。"""

from __future__ import annotations

from dataclasses import dataclass, field

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
    from backend.services.grid_builder_helpers import assign_commit_lane, find_matched_idx

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
    from backend.services.grid_builder_helpers import update_active_lanes

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
        # tip が row=0 にある（ヘッダー行に直接表示）→ 配置済みレーンを使用。
        # tip が row>0 にある（ダミーノードで代替）→ ダミーの位置である指定レーンを使用。
        if tip_h in placed and placed[tip_h].row == 0:
            target_lane = placed[tip_h].lane
        else:
            target_lane = tip_lane.get(tip_h)
        if target_lane is None:
            continue
        lane_to_names.setdefault(target_lane, []).append(b.name)
        lane_to_color[target_lane] = color_map.get(b.name, GRID_COLORS[0])
    return [
        GridBranchLabel(lane=ln, names=names, color=lane_to_color[ln])
        for ln, names in lane_to_names.items()
    ]
