"""レーンノード・エッジ構築関数。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_layout import (
    LANE_OFFSET,
    LANE_WIDTH,
    MARGIN_TOP,
    ROW_SPACING,
    LayoutEdge,
    LayoutNode,
)


def build_lane_nodes(
    rows: list[Commit],
    hash_to_lane: dict[str, int],
) -> list[LayoutNode]:
    """各コミットに座標とレーンを付与した LayoutNode リストを返す。

    Args:
        rows: 表示対象コミットのリスト（降順）。
        hash_to_lane: ハッシュ→レーン番号の辞書。

    Returns:
        LayoutNode のリスト。
    """
    nodes = []
    for i, commit in enumerate(rows):
        lane = hash_to_lane.get(commit.hash, 0)
        x = lane * LANE_WIDTH + LANE_OFFSET
        y = MARGIN_TOP + i * ROW_SPACING
        nodes.append(LayoutNode(commit=commit, x=x, y=y, lane=lane))
    return nodes


def build_lane_edges(
    rows: list[Commit],
    parents: dict[str, list[str]],
    row_set: set[str],
) -> list[LayoutEdge]:
    """visible set 内のエッジ一覧を返す。

    Args:
        rows: 表示対象コミットのリスト。
        parents: 子→親ハッシュのリスト辞書。
        row_set: 表示対象コミットのハッシュ集合。

    Returns:
        LayoutEdge のリスト。
    """
    edges = []
    for r in rows:
        for ph in parents.get(r.hash, []):
            if ph in row_set:
                edges.append(LayoutEdge(child_hash=r.hash, parent_hash=ph))
    return edges
