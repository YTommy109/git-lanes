"""SVG エッジ・ヘッダー・キャンバスのビルダー関数群。"""

from __future__ import annotations

from backend.services.graph_models import SvgBranchHeader, SvgEdge, SvgLabel
from backend.services.grid_models import GRID_ORIGIN_X, GRID_ORIGIN_Y, GRID_SPACING, GridLayout


def _cx(lane: int) -> float:
    """レーン番号を SVG X 座標に変換する。"""
    return float(GRID_ORIGIN_X + lane * GRID_SPACING)


def _cy(row: int) -> float:
    """行番号を SVG Y 座標に変換する。"""
    return float(GRID_ORIGIN_Y + row * GRID_SPACING)


def build_svg_edges(layout: GridLayout) -> list[SvgEdge]:
    """GridEdge リストを SvgEdge リストに変換する。

    Args:
        layout: グリッドレイアウト。

    Returns:
        SvgEdge のリスト。
    """
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


def build_svg_headers(layout: GridLayout) -> list[SvgBranchHeader]:
    """GridBranchLabel リストを SvgBranchHeader リストに変換する。

    Args:
        layout: グリッドレイアウト。

    Returns:
        SvgBranchHeader のリスト。
    """
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


def calc_canvas(layout: GridLayout) -> tuple[float, float]:
    """キャンバスのサイズを計算する。

    Args:
        layout: グリッドレイアウト。

    Returns:
        (幅, 高さ) のタプル。
    """
    all_cx = [_cx(n.lane) for n in layout.nodes] or [100.0]
    all_cy = [_cy(n.row) for n in layout.nodes] or [100.0]
    return max(all_cx) + 60.0, max(all_cy) + 40.0
