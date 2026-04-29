# backend/services/graph_builder_phases.py
"""Phase 2〜3: レイヤー構築の実装。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_builder_helpers import (
    _is_ready,
    _place_parent,
    _realize_dummy,
)
from backend.services.graph_models import (
    LANE_COLORS,
    GraphBranch,
    GraphLayer,
    GraphLine,
    GraphNode,
)


def _process_ready_node(
    node: GraphNode,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
) -> None:
    """確定済みノードの親をカレントレイヤーに配置する。"""
    for i, ph in enumerate(parents.get(node.commit.hash, [])):
        if i == 0:
            line = node.primary_line
        else:
            color = LANE_COLORS[color_idx[0] % len(LANE_COLORS)]
            color_idx[0] += 1
            branch = GraphBranch(color=color)
            line = GraphLine(branch=branch, color=color)
            branch.main_line = line
            line.nodes.append(node)
        _place_parent(
            ph, line, node, curr, commit_to_node, children_map, commit_map,
            edge_colors, edge_is_main,
        )


def _process_layer(
    prev: GraphLayer,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
) -> None:
    """prev の各ノードを評価して curr にノードを追加する。"""
    for node in prev.nodes:
        if node.dummy:
            _realize_dummy(node, curr, commit_to_node, children_map)
        else:
            _process_ready_node(
                node, curr, commit_to_node, children_map, parents,
                commit_map, color_idx, edge_colors, edge_is_main,
            )


def build_layers(
    layer0: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
) -> tuple[list[GraphLayer], dict[tuple[str, str], str], dict[tuple[str, str], bool]]:
    """Phase 3: 前レイヤーを処理して次レイヤーを生成するループを繰り返す。

    Returns:
        (layers, edge_colors, edge_is_main):
            edge_colors は (child_hash, parent_hash) → 線の色。
            edge_is_main は (child_hash, parent_hash) → HEAD ブランチのラインか。
    """
    layers = [layer0]
    edge_colors: dict[tuple[str, str], str] = {}
    edge_is_main: dict[tuple[str, str], bool] = {}
    prev = layer0
    while True:
        curr = GraphLayer(index=len(layers))
        _process_layer(
            prev, curr, commit_to_node, children_map, parents,
            commit_map, color_idx, edge_colors, edge_is_main,
        )
        if not curr.nodes:
            break
        layers.append(curr)
        prev = curr
    return layers, edge_colors, edge_is_main
