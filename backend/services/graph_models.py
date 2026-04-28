# backend/services/graph_models.py
"""グラフ描画のデータモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.models import Commit

LANE_COLORS: list[str] = [
    "#4a9cf6",
    "#f6974a",
    "#4af690",
    "#f64a7b",
    "#af4af6",
    "#f6e44a",
    "#4af6f0",
    "#f6a84a",
]
SPACING_X: float = 30.0
SPACING_Y: float = 60.0
MARGIN_TOP: float = 30.0


@dataclass
class GraphBranch:
    """論理的なブランチ/レーン。"""

    color: str
    refs: list[str] = field(default_factory=list)
    main_line: GraphLine | None = None
    tip_node: GraphNode | None = None


@dataclass
class GraphLine:
    """ブランチの流れを表すラインセグメント。X 座標をレイヤー間で引き継ぐ。"""

    branch: GraphBranch
    color: str
    is_main: bool = False
    nodes: list[GraphNode] = field(default_factory=list)
    x: float = 0.0
    positioned: bool = False


@dataclass
class GraphNode:
    """個々のコミット。dummy=True は子未確定のプレースホルダー。"""

    commit: Commit
    layer: GraphLayer
    primary_line: GraphLine
    dummy: bool = False
    x: float = 0.0
    parent_nodes: list[GraphNode] = field(default_factory=list)


@dataclass
class GraphLayer:
    """時系列の 1 段（Y 座標単位）。"""

    index: int
    nodes: list[GraphNode] = field(default_factory=list)
    y: float = 0.0


@dataclass
class SvgNode:
    """SVG テンプレートへ渡すノード情報。"""

    cx: float
    cy: float
    color: str
    commit: Commit
    labels: list[str]


@dataclass
class SvgEdge:
    """SVG テンプレートへ渡すエッジ情報。"""

    d: str
    color: str


@dataclass
class GraphResult:
    """build_graph() の返り値。"""

    nodes: list[SvgNode]
    edges: list[SvgEdge]
    canvas_width: float
    canvas_height: float
