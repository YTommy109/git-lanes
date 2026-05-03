# backend/services/grid_coords.py
"""GridLayout → GraphResult（SVG 変換）。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_models import (
    GraphResult,
    NodeType,
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


def to_svg(
    layout: GridLayout,
    commits: list[Commit],
    parents: dict[str, list[str]],
    tag_map: dict[str, list[str]] | None = None,
) -> GraphResult:
    """GridLayout を GraphResult に変換する。

    Args:
        layout: グリッドレイアウト（build_layout の返り値）。
        commits: コミットのリスト（SvgNode.commit に渡す）。
        parents: コミットハッシュ → 親ハッシュリスト のマップ。
        tag_map: コミットハッシュ → タグ名リストのマップ。非 tip コミットのバッジ表示に使う。

    Returns:
        SVG テンプレートへ渡す GraphResult。
    """
    commit_map: dict[str, Commit] = {c.hash: c for c in commits}
    svg_nodes = _build_svg_nodes(layout, commit_map, parents, tag_map or {})
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


def _resolve_node_type(
    node_hash: str,
    row: int,
    parents: dict[str, list[str]],
) -> NodeType:
    """コミットのノードタイプを決定する。"""
    node_parents = parents.get(node_hash, [])
    if len(node_parents) == 0:
        return "root"
    if len(node_parents) >= 2:
        return "merge"
    if row == 0:
        return "tip"
    return "regular"


def _build_svg_nodes(
    layout: GridLayout,
    commit_map: dict[str, Commit],
    parents: dict[str, list[str]],
    tag_map: dict[str, list[str]],
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
        node_type = _resolve_node_type(node.hash, node.row, parents)
        # tip ノードのタグはヘッダー行に表示するため、バッジは付けない
        labels: list[SvgLabel] = []
        if node_type != "tip":
            tag_names = tag_map.get(node.hash, [])
            if tag_names:
                labels.append(SvgLabel(text=", ".join(tag_names), kind="tag"))
        result.append(
            SvgNode(
                cx=_cx(node.lane),
                cy=_cy(node.row),
                color=node.color,
                commit=commit,
                labels=labels,
                node_type=node_type,
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
    dummy_lanes = {n.lane for n in layout.nodes if n.kind == "dummy" and n.row == 0}
    result: list[SvgBranchHeader] = []
    for label in layout.branch_labels:
        has_dummy = label.lane in dummy_lanes
        cx = _cx(label.lane)
        result.append(
            SvgBranchHeader(
                cx=cx,
                cy=label_y,
                labels=[SvgLabel(text=n, kind="branch") for n in label.names],
                color=label.color,
                display_text=", ".join(label.names),
                connector_to_x=cx if has_dummy else None,
                connector_to_y=float(_cy(0)) if has_dummy else None,
            )
        )
    return result


def _calc_canvas(layout: GridLayout) -> tuple[float, float]:
    """キャンバスのサイズを計算する。"""
    all_cx = [_cx(n.lane) for n in layout.nodes] or [100.0]
    all_cy = [_cy(n.row) for n in layout.nodes] or [100.0]
    return max(all_cx) + 60.0, max(all_cy) + 40.0
