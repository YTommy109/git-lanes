# backend/services/graph_coords.py
"""Phase 4: 座標計算と SVG 変換。"""

from __future__ import annotations

from backend.services.graph_builder_helpers import _apply_overlap_avoidance, _make_branch_headers
from backend.services.graph_models import (
    MARGIN_TOP,
    SPACING_X,
    SPACING_Y,
    GraphLayer,
    GraphNode,
    GraphResult,
    NodeType,
    SvgEdge,
    SvgLabel,
    SvgNode,
)


def assign_coords(layers: list[GraphLayer]) -> None:
    """各ノードの x/y 座標をインプレースで付与する。同一ラインの x は引き継がれる。"""
    for layer in layers:
        layer.y = MARGIN_TOP + layer.index * SPACING_Y
        last_x = 0.0
        for node in layer.nodes:
            if node.primary_line.is_main:
                last_x += 1.0  # メインラインに追加スペース（gitup の branchMainLine += 2 相当）
            if node.primary_line.positioned:
                x = node.primary_line.x
                if x <= last_x:
                    x = last_x + 1.0
            else:
                x = last_x + 1.0
            node.x = x
            node.primary_line.x = x
            node.primary_line.positioned = True
            last_x = x


def _resolve_node_type(
    node: GraphNode,
    layer: GraphLayer,
    parents: dict[str, list[str]],
) -> NodeType:
    """ノードの種別を返す。

    Args:
        node: 種別を判定する対象ノード。
        layer: ノードが属するレイヤー。
        parents: コミットハッシュをキー、親ハッシュのリストを値とする辞書。

    Returns:
        判定された NodeType 文字列。
    """
    if layer.index == 0 and not node.dummy:
        return "tip"
    parent_hashes = parents.get(node.commit.hash, [])
    if not parent_hashes:
        return "root"
    if len(parent_hashes) >= 2:
        return "merge"
    return "regular"


def _make_svg_node(
    node: GraphNode,
    layer: GraphLayer,
    parents: dict[str, list[str]],
    labels: dict[str, list[SvgLabel]],
) -> SvgNode:
    """単一ノードの SvgNode を生成する。"""
    return SvgNode(
        cx=node.x * SPACING_X,
        cy=layer.y,
        color=node.primary_line.color,
        commit=node.commit,
        labels=labels.get(node.commit.hash, []),
        node_type=_resolve_node_type(node, layer, parents),
    )


def _make_svg_edges(
    node: GraphNode,
    layer: GraphLayer,
    parents: dict[str, list[str]],
    commit_to_node: dict[str, GraphNode],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
) -> list[SvgEdge]:
    """単一ノードから親へのエッジリストを生成する。ダミー親はスキップする。"""
    edges: list[SvgEdge] = []
    for ph in parents.get(node.commit.hash, []):
        pnode = commit_to_node.get(ph)
        if pnode is None or pnode.dummy:
            continue
        color = edge_colors.get((node.commit.hash, ph), node.primary_line.color)
        is_main = edge_is_main.get((node.commit.hash, ph), False)
        x1, y1 = node.x * SPACING_X, layer.y
        x2, y2 = pnode.x * SPACING_X, pnode.layer.y
        edges.append(
            SvgEdge(d=f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}", color=color, is_main=is_main)
        )
    return edges


def to_svg(
    layers: list[GraphLayer],
    parents: dict[str, list[str]],
    commit_to_node: dict[str, GraphNode],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
    labels_by_hash: dict[str, list[SvgLabel]],
) -> GraphResult:
    """座標付きレイヤーを SvgNode/SvgEdge に変換して GraphResult を返す。"""
    svg_nodes: list[SvgNode] = []
    svg_edges: list[SvgEdge] = []
    for layer in layers:
        for node in layer.nodes:
            if node.dummy:
                continue
            svg_nodes.append(_make_svg_node(node, layer, parents, labels_by_hash))
            svg_edges.extend(
                _make_svg_edges(node, layer, parents, commit_to_node, edge_colors, edge_is_main)
            )
    max_cx = max((n.cx for n in svg_nodes), default=0.0)
    max_cy = max((n.cy for n in svg_nodes), default=0.0)
    branch_headers = _make_branch_headers(layers, labels_by_hash)
    _apply_overlap_avoidance(branch_headers)
    return GraphResult(
        nodes=svg_nodes,
        edges=svg_edges,
        branch_headers=branch_headers,
        canvas_width=max_cx + 150.0,
        canvas_height=max_cy + 80.0,
    )
