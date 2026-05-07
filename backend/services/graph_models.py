# backend/services/graph_models.py
"""SVG グラフ描画の出力データモデル。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.models import Commit

NodeType = Literal["tip", "root", "merge", "regular"]
LabelKind = Literal["head", "branch", "tag"]


@dataclass
class SvgLabel:
    """ブランチ名・タグ・HEAD ラベルの種別付きデータ。"""

    text: str
    kind: LabelKind


@dataclass
class SvgBranchHeader:
    """SVG ヘッダー行に描画するブランチ名ラベル。"""

    cx: float
    color: str
    label_entries: list[tuple[float, SvgLabel]]
    connector_to_x: float | None = None  # 実コミット円の cx（ダミー tip のみ設定）
    connector_to_y: float | None = None  # 実コミット円の cy（ダミー tip のみ設定）


@dataclass
class SvgNode:
    """SVG テンプレートへ渡すノード情報。"""

    cx: float
    cy: float
    lane: int
    row: int
    color: str
    commit: Commit
    labels: list[SvgLabel]
    node_type: NodeType = "regular"


@dataclass
class SvgEdge:
    """SVG テンプレートへ渡すエッジ情報。"""

    d: str
    color: str
    dashed: bool = False


@dataclass
class GraphResult:
    """build_grid() の返り値。"""

    nodes: list[SvgNode]
    edges: list[SvgEdge]
    branch_headers: list[SvgBranchHeader]
    canvas_width: float
    canvas_height: float
