# backend/services/grid_builder_layout.py
"""グリッドグラフエンジンのレイアウト構築関数群。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.grid_models import GRID_COLORS, GridEdge, GridLayout, GridNode


def _add_dummy_edges_for_branch(
    layout: GridLayout,
    dl: int,
    tl: int,
    tr: int,
    dc: str,
) -> None:
    """ダミーノードから tip コミットへのエッジを生成する。"""
    from backend.services.grid_builder_helpers import _e

    if dl == tl:
        layout.edges.append(_e(dl, 0, tl, tr, dc, True))
        return
    cl, cr = dl, 0
    for mid_row in range(1, tr):
        layout.nodes.append(GridNode(hash=None, lane=cl, row=mid_row, kind="joint", color=dc))
        layout.edges.append(_e(cl, cr, cl, mid_row, dc, True))
        cr = mid_row
    layout.edges.append(_e(cl, cr, tl, tr, dc, True))


def build_dummy_nodes(
    layout: GridLayout,
    branches: list[Branch],
    tip_lane: dict[str, int],
    color_map: dict[str, str],
    placed: dict[str, GridNode],
) -> None:
    """branch の tip が row=0 でない場合のダミーを生成する。

    Args:
        layout: レイアウト（ノード・エッジを追加する）。
        branches: ブランチのリスト。
        tip_lane: ブランチ tip からレーン番号へのマップ。
        color_map: ブランチ名から色へのマップ。
        placed: 配置済みコミットのマップ。
    """
    for b in branches:
        tip_h = b.tip_hash
        if tip_h not in placed or placed[tip_h].row == 0:
            continue
        tip_node = placed[tip_h]
        dl = tip_lane.get(tip_h, tip_node.lane)
        dc = color_map.get(b.name, GRID_COLORS[0])
        layout.nodes.append(GridNode(hash=None, lane=dl, row=0, kind="dummy", color=dc))
        _add_dummy_edges_for_branch(layout, dl, tip_node.lane, tip_node.row, dc)


def build_edge_graph(
    layout: GridLayout,
    parents: dict[str, list[str]],
    placed: dict[str, GridNode],
) -> None:
    """各コミットから親へのエッジを生成する。

    Args:
        layout: レイアウト（エッジを追加する）。
        parents: コミットハッシュから親ハッシュリストへのマップ。
        placed: 配置済みコミットのマップ。
    """
    from backend.services.grid_builder_helpers import add_joint_edges

    for node in layout.nodes:
        if node.kind != "commit":
            continue
        for p_hash in parents.get(node.hash or "", []):
            if p_hash not in placed:
                continue
            p_node = placed[p_hash]
            if node.lane == p_node.lane or abs(p_node.row - node.row) == 1:
                layout.edges.append(
                    GridEdge(
                        from_lane=node.lane,
                        from_row=node.row,
                        to_lane=p_node.lane,
                        to_row=p_node.row,
                        color=node.color,
                        dashed=False,
                    )
                )
            else:
                add_joint_edges(layout, node, p_node)
