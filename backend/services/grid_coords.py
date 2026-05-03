# backend/services/grid_coords.py
"""GridLayout → GraphResult（SVG 変換）。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_models import (
    GraphResult,
    SvgBranchHeader,
    SvgEdge,
    SvgLabel,
    SvgNode,
)
from backend.services.grid_models import (
    GRID_ORIGIN_X,
    GRID_ORIGIN_Y,
    GRID_SPACING,
    GridLayout,
)


def _cx(lane: int) -> float:
    """レーン番号を SVG X 座標に変換する。"""
    return float(GRID_ORIGIN_X + lane * GRID_SPACING)


def _cy(row: int) -> float:
    """行番号を SVG Y 座標に変換する。"""
    return float(GRID_ORIGIN_Y + row * GRID_SPACING)


def to_svg(layout: GridLayout, commits: list[Commit]) -> GraphResult:
    """GridLayout を GraphResult に変換する。

    Args:
        layout: グリッドレイアウト（build_layout の返り値）。
        commits: コミットのリスト（SvgNode.commit に渡す）。

    Returns:
        SVG テンプレートへ渡す GraphResult。
    """
    commit_map: dict[str, Commit] = {c.hash: c for c in commits}
    svg_nodes = _build_svg_nodes(layout, commit_map)
    svg_edges = _build_svg_edges(layout)
    svg_headers = _build_svg_headers(layout)
    canvas_width, canvas_height = _calc_canvas(layout)
    return GraphResult(
        nodes=svg_nodes,
        edges=svg_edges,
        branch_headers=svg_headers,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )


def _build_svg_nodes(
    layout: GridLayout,
    commit_map: dict[str, Commit],
) -> list[SvgNode]:
    """GridNode リストを SvgNode リストに変換する。"""
    result: list[SvgNode] = []
    for node in layout.nodes:
        if node.kind == "joint":
            continue  # joint は SVG に描画しない
        if node.hash is None:
            continue  # hash なし（一部 dummy）は skip
        commit = commit_map.get(node.hash)
        if commit is None:
            continue
        result.append(
            SvgNode(
                cx=_cx(node.lane),
                cy=_cy(node.row),
                color=node.color,
                commit=commit,
                labels=[],
                node_type="regular",
            )
        )
    return result


def _build_svg_edges(layout: GridLayout) -> list[SvgEdge]:
    """GridEdge リストを SvgEdge リストに変換する。"""
    result: list[SvgEdge] = []
    for edge in layout.edges:
        x1, y1 = _cx(edge.from_lane), _cy(edge.from_row)
        x2, y2 = _cx(edge.to_lane), _cy(edge.to_row)
        result.append(
            SvgEdge(
                d=f"M {x1} {y1} L {x2} {y2}",
                color=edge.color,
                is_main=False,
                dashed=edge.dashed,
            )
        )
    return result


def _build_svg_headers(layout: GridLayout) -> list[SvgBranchHeader]:
    """GridBranchLabel リストを SvgBranchHeader リストに変換する。"""
    label_y = float(GRID_ORIGIN_Y - GRID_SPACING)
    result: list[SvgBranchHeader] = []
    for label in layout.branch_labels:
        result.append(
            SvgBranchHeader(
                cx=_cx(label.lane),
                cy=label_y,
                labels=[SvgLabel(text=n, kind="branch") for n in label.names],
                color=label.color,
                display_text=", ".join(label.names),
            )
        )
    return result


def _calc_canvas(layout: GridLayout) -> tuple[float, float]:
    """キャンバスのサイズを計算する。"""
    all_cx = [_cx(n.lane) for n in layout.nodes] or [100.0]
    all_cy = [_cy(n.row) for n in layout.nodes] or [100.0]
    return max(all_cx) + 60.0, max(all_cy) + 40.0
