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


def build_layer0(
    tips: list[Commit],
    layer: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    labels: dict[str, list[str]],
    color_idx: list[int],
) -> None:
    """Phase 2: Layer 0 を構築し commit_to_node を初期化する。"""
    for tip in tips:
        color = LANE_COLORS[color_idx[0] % len(LANE_COLORS)]
        color_idx[0] += 1
        branch = GraphBranch(color=color, refs=labels.get(tip.hash, []))
        line = GraphLine(branch=branch, color=color, is_main=True)
        branch.main_line = line
        node = GraphNode(
            commit=tip,
            layer=layer,
            primary_line=line,
            dummy=not _is_ready(tip.hash, layer, commit_to_node, children_map),
        )
        branch.tip_node = node
        line.nodes.append(node)
        layer.nodes.append(node)
        commit_to_node[tip.hash] = node


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
    """ダミーノードを実レイヤーに具現化する。

    Args:
        node: ダミーノードのインスタンス。
        curr: カレントレイヤー。
        commit_to_node: コミットハッシュ→ノードのマッピング。
        children_map: コミットハッシュ→子コミットハッシュのマッピング。
    """
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
        if not curr.nodes:
            break
        layers.append(curr)
        prev = curr
    return layers, edge_colors
