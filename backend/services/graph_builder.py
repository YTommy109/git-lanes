# backend/services/graph_builder.py
"""gitup GIGraph アルゴリズムの Python 実装。"""

from __future__ import annotations

from backend.models import Branch, Commit, Tag
from backend.services.graph_builder_phases import (
    _is_ready,  # noqa: F401  テストから graph_builder 経由でアクセスされる
    build_layers,
)
from backend.services.graph_coords import assign_coords, to_svg
from backend.services.graph_models import (
    LANE_COLORS,
    GraphBranch,
    GraphLayer,
    GraphLine,
    GraphNode,
    GraphResult,
)


def _build_children_map(parents: dict[str, list[str]]) -> dict[str, list[str]]:
    """parents dict から {parent_hash: [child_hash]} の逆引き辞書を構築する。"""
    children: dict[str, list[str]] = {}
    for child, plist in parents.items():
        for p in plist:
            children.setdefault(p, []).append(child)
    return children


def _collect_tips(
    commit_map: dict[str, Commit],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None,
) -> list[Commit]:
    """TIP コミットを HEAD → ローカル → リモート → タグの順で収集する（重複排除済み）。"""
    seen: set[str] = set()
    result: list[Commit] = []

    def _add(h: str) -> None:
        if h and h not in seen and h in commit_map:
            seen.add(h)
            result.append(commit_map[h])

    if head_hash:
        _add(head_hash)
    for b in sorted(branches, key=lambda b: (b.is_remote, b.name)):
        _add(b.tip_hash)
    for t in tags:
        _add(t.commit_hash)
    return result


def _build_labels(
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None,
) -> dict[str, list[str]]:
    """ブランチ・タグ・HEAD のラベル辞書を構築する。"""
    labels: dict[str, list[str]] = {}
    if head_hash:
        labels.setdefault(head_hash, []).insert(0, "HEAD")
    for b in branches:
        labels.setdefault(b.tip_hash, []).append(b.name)
    for t in tags:
        labels.setdefault(t.commit_hash, []).append(t.name)
    return labels


def _build_layer0(
    tips: list[Commit],
    layer: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    labels: dict[str, list[str]],
    color_idx: list[int],
) -> None:
    """Phase 2: Layer 0 を構築し commit_to_node を初期化する。"""
    for tip in tips:
        color = LANE_COLORS[color_idx[0] % len(LANE_COLORS)]
        color_idx[0] += 1
        branch = GraphBranch(color=color, refs=labels.get(tip.hash, []))
        line = GraphLine(branch=branch, color=color, is_main=True)
        branch.main_line = line
        node = GraphNode(
            commit=tip,
            layer=layer,
            primary_line=line,
            dummy=not _is_ready(tip.hash, layer, commit_to_node, children_map),
        )
        branch.tip_node = node
        line.nodes.append(node)
        layer.nodes.append(node)
        commit_to_node[tip.hash] = node


def build_graph(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GraphResult:
    """gitup GIGraph アルゴリズムでグラフを構築して SVG データを返す。

    Args:
        commits: 対象リポジトリの全コミット。
        parents: {child_hash: [parent_hash, ...]} の親子関係辞書。
        branches: リポジトリの全ブランチ。
        tags: リポジトリの全タグ。
        head_hash: HEAD コミットのハッシュ。None の場合は HEAD ラベルを付けない。

    Returns:
        SVG 描画用の GraphResult。
    """
    if not commits:
        return GraphResult(nodes=[], edges=[], canvas_width=300.0, canvas_height=100.0)

    commit_map = {c.hash: c for c in commits}
    children_map = _build_children_map(parents)
    labels = _build_labels(branches, tags, head_hash)

    tips = _collect_tips(commit_map, branches, tags, head_hash)
    if not tips:
        return GraphResult(nodes=[], edges=[], canvas_width=300.0, canvas_height=100.0)

    layer0 = GraphLayer(index=0)
    commit_to_node: dict[str, GraphNode] = {}
    color_idx = [0]
    _build_layer0(tips, layer0, commit_to_node, children_map, labels, color_idx)

    layers, edge_colors = build_layers(
        layer0, commit_to_node, children_map, parents, commit_map, color_idx
    )
    assign_coords(layers)
    return to_svg(layers, parents, commit_to_node, edge_colors, labels)
