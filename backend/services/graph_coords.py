# backend/services/graph_coords.py
"""Phase 4: 座標計算と SVG 変換。"""

from __future__ import annotations

from backend.services.graph_models import (
    MARGIN_TOP,
    SPACING_X,
    SPACING_Y,
    GraphLayer,
    GraphNode,
    GraphResult,
    SvgEdge,
    SvgNode,
)


def assign_coords(layers: list[GraphLayer]) -> None:
    """各ノードの x/y 座標をインプレースで付与する。同一ラインの x は引き継がれる。"""
    for layer in layers:
        layer.y = MARGIN_TOP + layer.index * SPACING_Y
        last_x = 0.0
        for node in layer.nodes:
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


def to_svg(
    layers: list[GraphLayer],
    parents: dict[str, list[str]],
    commit_to_node: dict[str, GraphNode],
    edge_colors: dict[tuple[str, str], str],
    labels_by_hash: dict[str, list[str]],
) -> GraphResult:
    """座標付きレイヤーを SvgNode/SvgEdge に変換して GraphResult を返す。

    エッジは commit_to_node の最終状態（ダミー解決済み）を参照して描画する。
    """
    svg_nodes: list[SvgNode] = []
    svg_edges: list[SvgEdge] = []

    for layer in layers:
        for node in layer.nodes:
            if node.dummy:
                continue
            svg_nodes.append(
                SvgNode(
                    cx=node.x * SPACING_X,
                    cy=layer.y,
                    color=node.primary_line.color,
                    commit=node.commit,
                    labels=labels_by_hash.get(node.commit.hash, []),
                )
            )
            for parent_hash in parents.get(node.commit.hash, []):
                parent_node = commit_to_node.get(parent_hash)
                if parent_node is None or parent_node.dummy:
                    continue
                color = edge_colors.get(
                    (node.commit.hash, parent_hash),
                    node.primary_line.color,
                )
                x1, y1 = node.x * SPACING_X, layer.y
                x2, y2 = parent_node.x * SPACING_X, parent_node.layer.y
                svg_edges.append(
                    SvgEdge(
                        d=f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}",
                        color=color,
                    )
                )

    max_cx = max((n.cx for n in svg_nodes), default=0.0)
    max_cy = max((n.cy for n in svg_nodes), default=0.0)
    return GraphResult(
        nodes=svg_nodes,
        edges=svg_edges,
        canvas_width=max_cx + 150.0,
        canvas_height=max_cy + 80.0,
    )
