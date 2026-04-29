# backend/services/graph_builder_helpers.py
"""graph_builder_phases の低レベルヘルパー関数。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_models import (
    SPACING_X,
    GraphLayer,
    GraphLine,
    GraphNode,
    SvgBranchHeader,
    SvgLabel,
)


def _is_ready(
    commit_hash: str,
    current_layer: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
) -> bool:
    """すべての子コミットが別レイヤーに実ノードとして確定済みなら True を返す。"""
    for child_hash in children_map.get(commit_hash, []):
        node = commit_to_node.get(child_hash)
        if node is None or node.dummy or node.layer is current_layer:
            return False
    return True


def _place_parent(
    ph: str,
    line: GraphLine,
    node: GraphNode,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    commit_map: dict[str, Commit],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
) -> None:
    """親コミットをカレントレイヤーに配置し edge_colors と edge_is_main を更新する。"""
    edge_colors[(node.commit.hash, ph)] = line.color
    edge_is_main[(node.commit.hash, ph)] = line.is_head_branch
    if ph in commit_to_node:
        line.nodes.append(commit_to_node[ph])
    elif ph in commit_map:
        ready = _is_ready(ph, curr, commit_to_node, children_map)
        pnode = GraphNode(commit=commit_map[ph], layer=curr, primary_line=line, dummy=not ready)
        line.nodes.append(pnode)
        curr.nodes.append(pnode)
        commit_to_node[ph] = pnode


def _realize_dummy(
    node: GraphNode,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
) -> None:
    """ダミーノードを次レイヤーに持ち越す（準備完了なら実ノードに昇格）。"""
    ready = _is_ready(node.commit.hash, curr, commit_to_node, children_map)
    new = GraphNode(
        commit=node.commit,
        layer=curr,
        primary_line=node.primary_line,
        dummy=not ready,
    )
    node.primary_line.nodes.append(new)
    curr.nodes.append(new)
    commit_to_node[node.commit.hash] = new


def _apply_overlap_avoidance(
    headers: list[SvgBranchHeader],
    char_width_px: float = 6.5,
    gap_px: float = 6.0,
) -> None:
    """右→左の順でヘッダーテキストを切り詰め、隣接ラベルの重なりを防ぐ。"""
    for i in range(len(headers) - 2, -1, -1):
        avail_px = (headers[i + 1].cx - headers[i].cx - gap_px) * (2**0.5)
        max_chars = max(1, int(avail_px / char_width_px))
        if len(headers[i].display_text) > max_chars:
            headers[i].display_text = headers[i].display_text[: max_chars - 1] + "…"


def _make_branch_headers(
    layers: list[GraphLayer],
    labels_by_hash: dict[str, list[SvgLabel]],
) -> list[SvgBranchHeader]:
    """Layer 0 の tip ノードからブランチヘッダーリストを生成する。"""
    if not layers:
        return []
    layer0 = layers[0]
    result: list[SvgBranchHeader] = []
    for node in layer0.nodes:
        if node.dummy:
            continue
        lbls = list(labels_by_hash.get(node.commit.hash, []))
        if not lbls:
            continue
        is_head = any(lbl.kind == "head" for lbl in lbls)
        display_text = " · ".join(
            f"[{lbl.text}]" if lbl.kind == "tag" else lbl.text for lbl in lbls
        )
        result.append(
            SvgBranchHeader(
                cx=node.x * SPACING_X,
                cy=layer0.y,
                labels=lbls,
                color=node.primary_line.color,
                display_text=display_text,
                is_head=is_head,
            )
        )
    return result
