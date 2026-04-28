# backend/services/graph_coords.py
"""Phase 4: 座標計算と SVG 変換。"""

from __future__ import annotations

from backend.services.graph_models import GraphLayer, GraphNode, GraphResult


def assign_coords(layers: list[GraphLayer]) -> None:
    """各ノードの x/y 座標をインプレースで付与する。"""
    pass  # Task 3 で実装


def to_svg(
    layers: list[GraphLayer],
    parents: dict[str, list[str]],
    commit_to_node: dict[str, GraphNode],
    edge_colors: dict[tuple[str, str], str],
    labels_by_hash: dict[str, list[str]],
) -> GraphResult:
    """座標付きレイヤーを SvgNode/SvgEdge に変換して GraphResult を返す。"""
    return GraphResult(nodes=[], edges=[], canvas_width=300.0, canvas_height=100.0)
