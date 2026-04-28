# backend/services/graph_builder_phases.py
"""Phase 2〜3: レイヤー構築の実装。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_models import (
    LANE_COLORS,
    GraphBranch,
    GraphLayer,
    GraphLine,
    GraphNode,
)


def _is_ready(
    commit_hash: str,
    current_layer: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
) -> bool:
    """すべての子コミットが別レイヤーに実ノードとして確定済みなら True を返す。"""
    for child_hash in children_map.get(commit_hash, []):
        node = commit_to_node.get(child_hash)
        if node is None or node.dummy or node.layer is current_layer:
            return False
    return True


def _place_parent(
    ph: str,
    line: GraphLine,
    node: GraphNode,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    commit_map: dict[str, Commit],
    edge_colors: dict[tuple[str, str], str],
) -> None:
    """親コミットをカレントレイヤーに配置し edge_colors を更新する。"""
    edge_colors[(node.commit.hash, ph)] = line.color
    if ph in commit_to_node:
        line.nodes.append(commit_to_node[ph])
    elif ph in commit_map:
        ready = _is_ready(ph, curr, commit_to_node, children_map)
        pnode = GraphNode(commit=commit_map[ph], layer=curr, primary_line=line, dummy=not ready)
        line.nodes.append(pnode)
        curr.nodes.append(pnode)
        commit_to_node[ph] = pnode


def _realize_dummy(
    node: GraphNode,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
) -> None:
    """ダミーノードを次レイヤーに持ち越す（準備完了なら実ノードに昇格）。"""
    ready = _is_ready(node.commit.hash, curr, commit_to_node, children_map)
    new = GraphNode(
        commit=node.commit,
        layer=curr,
        primary_line=node.primary_line,
        dummy=not ready,
    )
    node.primary_line.nodes.append(new)
    curr.nodes.append(new)
    commit_to_node[node.commit.hash] = new


def _process_ready_node(
    node: GraphNode,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
    edge_colors: dict[tuple[str, str], str],
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
        _place_parent(ph, line, node, curr, commit_to_node, children_map, commit_map, edge_colors)


def _process_layer(
    prev: GraphLayer,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
    edge_colors: dict[tuple[str, str], str],
) -> None:
    """prev の各ノードを評価して curr にノードを追加する。"""
    for node in prev.nodes:
        if node.dummy:
            _realize_dummy(node, curr, commit_to_node, children_map)
        else:
            _process_ready_node(
                node,
                curr,
                commit_to_node,
                children_map,
                parents,
                commit_map,
                color_idx,
                edge_colors,
            )


def build_layers(
    layer0: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
) -> tuple[list[GraphLayer], dict[tuple[str, str], str]]:
    """Phase 3: 前レイヤーを処理して次レイヤーを生成するループを繰り返す。

    Returns:
        (layers, edge_colors): edge_colors は (child_hash, parent_hash) → 線の色。
    """
    layers = [layer0]
    edge_colors: dict[tuple[str, str], str] = {}
    prev = layer0
    while True:
        curr = GraphLayer(index=len(layers))
        _process_layer(
            prev, curr, commit_to_node, children_map, parents, commit_map, color_idx, edge_colors
        )
        if not curr.nodes:
            break
        layers.append(curr)
        prev = curr
    return layers, edge_colors
