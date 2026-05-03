# backend/services/grid_builder.py
"""グリッドグラフエンジン。"""

from __future__ import annotations

from itertools import groupby

from backend.models import Branch, Commit, Tag
from backend.services.graph_models import GraphResult
from backend.services.grid_builder_helpers import init_branch_maps
from backend.services.grid_builder_layout import build_dummy_nodes, build_edge_graph
from backend.services.grid_builder_utils import (
    CommitState,
    _build_branch_labels,
    _process_one_commit,
)
from backend.services.grid_models import GridLayout, GridNode


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
    head_hash: str | None = None,
) -> GridLayout:
    """グリッドレイアウトを計算する。"""
    # tags は今後タグラベル表示に使用予定
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
    build_edge_graph(layout, parents, placed)
    for label in _build_branch_labels(branches, tip_lane, color_map, placed):
        layout.branch_labels.append(label)
    return layout


def build_grid(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GraphResult:
    """グリッドエンジンでグラフを構築して GraphResult を返す。

    Args:
        commits: コミットのリスト（新しい順）。
        parents: コミットハッシュ → 親ハッシュリスト のマップ。
        branches: ブランチのリスト。
        tags: タグのリスト（今後使用予定）。
        head_hash: HEAD コミットのハッシュ（今後使用予定）。

    Returns:
        SVG テンプレートへ渡す GraphResult。
    """
    from backend.services.grid_coords import to_svg

    layout = build_layout(commits, parents, branches, tags, head_hash)
    return to_svg(layout, commits, parents)
