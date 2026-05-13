# backend/services/grid_builder.py
"""グリッドグラフエンジン。"""

from __future__ import annotations

from itertools import groupby

from backend.models import Branch, Commit, Tag
from backend.services.fork_point import ForkData, compute_fork_data, sort_branches_by_fork_data
from backend.services.graph_models import GraphResult
from backend.services.grid_builder_helpers import init_branch_maps
from backend.services.grid_builder_layout import (
    _build_branch_labels,
    build_dummy_nodes,
    build_edge_graph,
)
from backend.services.grid_builder_utils import CommitState, _process_one_commit
from backend.services.grid_models import GridLayout, GridNode


def _build_tag_map(tags: list[Tag]) -> dict[str, list[str]]:
    """タグリストをコミットハッシュ→タグ名リストの辞書に変換する。"""
    result: dict[str, list[str]] = {}
    for tag in tags:
        result.setdefault(tag.commit_hash, []).append(tag.name)
    return result


def _place_commits(
    sorted_commits: list[Commit],
    parents: dict[str, list[str]],
    tip_lane: dict[str, int],
    tip_color: dict[str, str],
    used_lane_nums: set[int],
    layout: GridLayout,
) -> dict[str, GridNode]:
    """コミットをグリッドに配置し placed マップを返す。"""
    state = CommitState(used_lane_nums=used_lane_nums, color_idx=len(used_lane_nums))
    row = 0

    for _, group in groupby(sorted_commits, key=lambda c: c.committed_at):
        for commit in list(group):
            _process_one_commit(
                commit.hash,
                row,
                state,
                tip_lane,
                tip_color,
                parents.get(commit.hash, []),
                layout,
            )
        row += 1

    return state.placed


def build_layout(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    fork_data: dict[str, ForkData] | None = None,
    label_only_branches: list[Branch] | None = None,
) -> GridLayout:
    """グリッドレイアウトを計算する。"""
    if fork_data is None:
        fork_data = compute_fork_data(commits, parents, branches)
    sorted_branches = sort_branches_by_fork_data(branches, fork_data)
    tip_lane, color_map, tip_color = init_branch_maps(sorted_branches, label_only_branches)
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
    build_dummy_nodes(layout, sorted_branches, tip_lane, color_map, placed)
    build_edge_graph(layout, parents, placed)
    tag_map = _build_tag_map(tags)
    for label in _build_branch_labels(
        sorted_branches, tip_lane, color_map, placed, tag_map, label_only_branches
    ):
        layout.branch_labels.append(label)
    return layout


def build_grid(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    fork_data: dict[str, ForkData] | None = None,
    label_only_branches: list[Branch] | None = None,
) -> GraphResult:
    """グリッドエンジンでグラフを構築して GraphResult を返す。

    Args:
        commits: コミットのリスト（新しい順）。
        parents: コミットハッシュ → 親ハッシュリスト のマップ。
        branches: ブランチのリスト。
        tags: タグのリスト。
        fork_data: フォークポイントデータ（省略時は自動計算）。
        label_only_branches: レーンを消費せずラベルのみ表示するブランチ。

    Returns:
        SVG テンプレートへ渡す GraphResult。
    """
    from backend.services.grid_coords import to_svg

    tag_map = _build_tag_map(tags)
    layout = build_layout(commits, parents, branches, tags, fork_data, label_only_branches)
    return to_svg(layout, commits, parents, tag_map)
