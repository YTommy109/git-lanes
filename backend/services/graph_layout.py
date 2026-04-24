"""コミットグラフの単純レイアウト（単レーン）。"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models import Commit


@dataclass(frozen=True)
class LayoutNode:
    """レイアウト済みノード。"""

    commit: Commit
    x: float
    y: float


@dataclass(frozen=True)
class LayoutEdge:
    """表示対象内の親子エッジ。"""

    child_hash: str
    parent_hash: str


def build_single_lane_layout(
    rows: list[Commit], parents: dict[str, list[str]]
) -> tuple[list[LayoutNode], list[LayoutEdge]]:
    """上から新しい順のコミット列に縦方向の座標を割り当てる。

    Args:
        rows: ``committed_at`` 降順で並んだコミット。
        parents: 子ハッシュをキーとする親ハッシュのリスト。

    Returns:
        ノード一覧と、表示集合内に閉じたエッジ一覧。
    """
    spacing = 52.0
    margin_top = 36.0
    x = 56.0
    visible = {r.hash for r in rows}
    nodes = [LayoutNode(commit=r, x=x, y=margin_top + i * spacing) for i, r in enumerate(rows)]
    edges: list[LayoutEdge] = []
    for r in rows:
        for ph in parents.get(r.hash, []):
            if ph in visible:
                edges.append(LayoutEdge(child_hash=r.hash, parent_hash=ph))
    return nodes, edges
