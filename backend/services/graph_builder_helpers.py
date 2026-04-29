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
    existing = commit_to_node.get(ph)
    if existing and not existing.dummy:
        # 非ダミーノードが既存 → 別パスまたは Layer 0 の tip として確定済み
        line.nodes.append(existing)
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
    existing = commit_to_node.get(node.commit.hash)
    if existing and not existing.dummy and existing.layer is curr:
        # _place_parent が先に同一レイヤーへ実ノードを配置済み → 再利用（GitUp と同等）
        node.primary_line.nodes.append(existing)
        return
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
    """同一行（cy が等しい）内でのみ右→左の順でヘッダーテキストを切り詰め、重なりを防ぐ。"""
    row_groups: dict[float, list[SvgBranchHeader]] = {}
    for h in headers:
        row_groups.setdefault(h.cy, []).append(h)
    for row in row_groups.values():
        row.sort(key=lambda h: h.cx)
        for i in range(len(row) - 2, -1, -1):
            avail_px = (row[i + 1].cx - row[i].cx - gap_px) * (2**0.5)
            max_chars = max(1, int(avail_px / char_width_px))
            if len(row[i].display_text) > max_chars:
                row[i].display_text = row[i].display_text[: max_chars - 1] + "…"


def _make_branch_headers(
    layers: list[GraphLayer],
    labels_by_hash: dict[str, list[SvgLabel]],
) -> list[SvgBranchHeader]:
    """全レイヤーのブランチ tip ノードからブランチヘッダーリストを生成する。"""
    result: list[SvgBranchHeader] = []
    for layer in layers:
        for node in layer.nodes:
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
                    cy=layer.y,
                    labels=lbls,
                    color=node.primary_line.color,
                    display_text=display_text,
                    is_head=is_head,
                )
            )
    return result
