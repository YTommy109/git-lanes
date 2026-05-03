# backend/services/grid_coords.py
"""GridLayout → GraphResult（SVG 変換）。"""

from __future__ import annotations

from backend.services.graph_models import GraphResult
from backend.services.grid_models import GridLayout


def to_svg(layout: GridLayout) -> GraphResult:
    """GridLayout を GraphResult に変換する。"""
    return GraphResult(
        nodes=[],
        edges=[],
        branch_headers=[],
        canvas_width=100.0,
        canvas_height=100.0,
    )
