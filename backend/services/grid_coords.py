"""GridLayout → GraphResult（SVG 変換）。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_models import GraphResult, NodeType, SvgLabel, SvgNode
from backend.services.grid_models import GridLayout
from backend.services.grid_svg_parts import (
    _cx,
    _cy,
    build_svg_edges,
    build_svg_headers,
    calc_canvas,
)


def to_svg(
    layout: GridLayout,
    commits: list[Commit],
    parents: dict[str, list[str]],
    tag_map: dict[str, list[str]] | None = None,
) -> GraphResult:
    """GridLayout を GraphResult に変換する。

    Args:
        layout: グリッドレイアウト（build_layout の返り値）。
        commits: コミットのリスト（SvgNode.commit に渡す）。
        parents: コミットハッシュ → 親ハッシュリスト のマップ。
        tag_map: コミットハッシュ → タグ名リストのマップ。非 tip コミットのバッジ表示に使う。

    Returns:
        SVG テンプレートへ渡す GraphResult。
    """
    commit_map: dict[str, Commit] = {c.hash: c for c in commits}
    cw, ch = calc_canvas(layout)
    return GraphResult(
        nodes=_build_svg_nodes(layout, commit_map, parents, tag_map or {}),
        edges=build_svg_edges(layout),
        branch_headers=build_svg_headers(layout),
        canvas_width=cw,
        canvas_height=ch,
    )


def _resolve_node_type(
    node_hash: str,
    row: int,
    parents: dict[str, list[str]],
) -> NodeType:
    """コミットのノードタイプを決定する。"""
    node_parents = parents.get(node_hash, [])
    if not node_parents:
        return "root"
    if len(node_parents) >= 2:
        return "merge"
    return "tip" if row == 0 else "regular"


def _build_tag_labels(
    node_hash: str, node_type: NodeType, tag_map: dict[str, list[str]]
) -> list[SvgLabel]:
    """tip 以外のノードのタグバッジを返す。tip はヘッダー行に表示するためバッジは付けない。"""
    if node_type == "tip":
        return []
    tag_names = tag_map.get(node_hash, [])
    return [SvgLabel(text=", ".join(tag_names), kind="tag")] if tag_names else []


def _build_svg_nodes(
    layout: GridLayout,
    commit_map: dict[str, Commit],
    parents: dict[str, list[str]],
    tag_map: dict[str, list[str]],
) -> list[SvgNode]:
    """GridNode リストを SvgNode リストに変換する。"""
    result: list[SvgNode] = []
    for node in layout.nodes:
        if node.kind == "joint" or node.hash is None:
            continue
        commit = commit_map.get(node.hash)
        if commit is None:
            continue
        node_type = _resolve_node_type(node.hash, node.row, parents)
        result.append(
            SvgNode(
                cx=_cx(node.lane),
                cy=_cy(node.row),
                color=node.color,
                commit=commit,
                labels=_build_tag_labels(node.hash, node_type, tag_map),
                node_type=node_type,
            )
        )
    return result
