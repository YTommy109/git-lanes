# backend/services/grid_builder_layout.py
"""グリッドグラフエンジンのレイアウト構築関数群。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.grid_builder_helpers import _make_edge, add_joint_edges
from backend.services.grid_models import GRID_COLORS, GridBranchLabel, GridLayout, GridNode


def _add_dummy_edges_for_branch(
    layout: GridLayout,
    dl: int,
    tl: int,
    tr: int,
    dc: str,
) -> None:
    """ダミーノードから tip コミットへのエッジを生成する。"""
    if dl == tl:
        layout.edges.append(_make_edge(dl, 0, tl, tr, dc, True))
        return
    cl, cr = dl, 0
    for mid_row in range(1, tr):
        layout.nodes.append(GridNode(hash=None, lane=cl, row=mid_row, kind="joint", color=dc))
        layout.edges.append(_make_edge(cl, cr, cl, mid_row, dc, True))
        cr = mid_row
    layout.edges.append(_make_edge(cl, cr, tl, tr, dc, True))


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
    for node in layout.nodes:
        if node.kind != "commit":
            continue
        for p_hash in parents.get(node.hash or "", []):
            if p_hash not in placed:
                continue
            p_node = placed[p_hash]
            if node.lane == p_node.lane or abs(p_node.row - node.row) == 1:
                layout.edges.append(
                    _make_edge(node.lane, node.row, p_node.lane, p_node.row, node.color, False)
                )
            else:
                add_joint_edges(layout, node, p_node)


def _build_branch_labels(
    branches: list[Branch],
    tip_lane: dict[str, int],
    color_map: dict[str, str],
    placed: dict[str, GridNode],
    tag_map: dict[str, list[str]],
) -> list[GridBranchLabel]:
    """ブランチラベルリストを構築する。"""
    lane_to_names: dict[int, list[str]] = {}
    lane_to_color: dict[int, str] = {}
    for b in branches:
        tip_h = b.tip_hash
        # tip が row=0 にある（ヘッダー行に直接表示）→ 配置済みレーンを使用。
        # tip が row>0 にある（ダミーノードで代替）→ ダミーの位置である指定レーンを使用。
        if tip_h in placed and placed[tip_h].row == 0:
            target_lane = placed[tip_h].lane
        else:
            target_lane = tip_lane.get(tip_h)
        if target_lane is None:
            continue
        lane_to_names.setdefault(target_lane, []).append(b.name)
        lane_to_color[target_lane] = color_map.get(b.name, GRID_COLORS[0])
        for tag_name in tag_map.get(tip_h, []):
            lane_to_names[target_lane].append(f"[{tag_name}]")
    return [
        GridBranchLabel(lane=ln, names=names, color=lane_to_color[ln])
        for ln, names in lane_to_names.items()
    ]
