# backend/services/grid_builder.py
"""グリッドグラフエンジン。"""

from __future__ import annotations

from backend.models import Branch, Commit, Tag
from backend.services.graph_models import GraphResult
from backend.services.grid_models import GridLayout


def build_layout(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GridLayout:
    """グリッドレイアウトを計算する（テスト用）。"""
    return GridLayout()


def build_grid(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GraphResult:
    """グリッドエンジンでグラフを構築して GraphResult を返す。"""
    from backend.services.grid_coords import to_svg

    layout = build_layout(commits, parents, branches, tags, head_hash)
    return to_svg(layout)
