# backend/services/grid_models.py
"""グリッドグラフエンジンのデータモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal["commit", "dummy", "joint"]

GRID_COLORS: list[str] = [
    "#4a9cf6",
    "#f0883e",
    "#3fb950",
    "#e5534b",
    "#a371f7",
    "#f778ba",
    "#39c5cf",
    "#d4a72c",
]

GRID_SPACING: int = 30
GRID_ORIGIN_X: int = 20  # レーン N の cx = GRID_ORIGIN_X + N * GRID_SPACING
GRID_ORIGIN_Y: int = 72  # 行 M の cy = GRID_ORIGIN_Y + M * GRID_SPACING


@dataclass
class GridNode:
    """グリッド座標上のノード。joint は hash=None。"""

    hash: str | None
    lane: int
    row: int
    kind: NodeKind
    color: str


@dataclass
class GridEdge:
    """グリッド座標上のエッジ。"""

    from_lane: int
    from_row: int
    to_lane: int
    to_row: int
    color: str
    dashed: bool


@dataclass
class GridBranchLabel:
    """ブランチ名ラベル情報。"""

    lane: int
    names: list[str]
    color: str


@dataclass
class GridLayout:
    """build_layout() の返り値（テスト用中間表現）。"""

    nodes: list[GridNode] = field(default_factory=list)
    edges: list[GridEdge] = field(default_factory=list)
    branch_labels: list[GridBranchLabel] = field(default_factory=list)
