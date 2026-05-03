# tests/unit/test_grid_builder.py
"""grid_builder の単体テスト。11 ケース対応。"""

from __future__ import annotations

from backend.models import Branch, Commit
from backend.services.grid_models import GridLayout, NodeKind

_REPO = "test-repo"


def _c(h: str, parents: list[str], at: int = 0) -> Commit:
    """テスト用 Commit を生成する。hash は短い文字列でそのまま使う。"""
    return Commit(
        hash=h,
        short_hash=h[:7] if len(h) >= 7 else h,
        message="test",
        author_name="t",
        author_email="t@t.com",
        committed_at=at,
        repo_id=_REPO,
    )


def _b(name: str, tip: str) -> Branch:
    """テスト用 Branch を生成する。"""
    return Branch(name=name, repo_id=_REPO, tip_hash=tip, is_remote=0)


def _p(commits: list[Commit], edges: dict[str, list[str]]) -> dict[str, list[str]]:
    """コミットリストと親辺から parents dict を生成する。"""
    return {c.hash: edges.get(c.hash, []) for c in commits}


def assert_node(
    layout: GridLayout,
    h: str,
    lane: int,
    row: int,
    kind: NodeKind,
) -> None:
    """ハッシュでノードを探してアサートする。"""
    node = next((n for n in layout.nodes if n.hash == h), None)
    node_list = [(n.hash, n.lane, n.row) for n in layout.nodes]
    assert node is not None, f"ノード '{h}' が見つからない。nodes={node_list}"
    assert node.lane == lane, f"'{h}' lane: 実際={node.lane} 期待={lane}"
    assert node.row == row, f"'{h}' row: 実際={node.row} 期待={row}"
    assert node.kind == kind, f"'{h}' kind: 実際={node.kind} 期待={kind}"


def assert_edge(
    layout: GridLayout,
    from_h: str,
    to_h: str,
    dashed: bool,
) -> None:
    """コミットハッシュでエッジを探してアサートする。"""
    from_node = next((n for n in layout.nodes if n.hash == from_h), None)
    to_node = next((n for n in layout.nodes if n.hash == to_h), None)
    assert from_node is not None, f"from ノード '{from_h}' が見つからない"
    assert to_node is not None, f"to ノード '{to_h}' が見つからない"
    edge = next(
        (
            e
            for e in layout.edges
            if (
                e.from_lane == from_node.lane
                and e.from_row == from_node.row
                and e.to_lane == to_node.lane
                and e.to_row == to_node.row
            )
        ),
        None,
    )
    edge_list = [(e.from_lane, e.from_row, e.to_lane, e.to_row) for e in layout.edges]
    assert edge is not None, (
        f"エッジ '{from_h}'({from_node.lane},{from_node.row})"
        f"→'{to_h}'({to_node.lane},{to_node.row}) が見つからない。"
        f"edges={edge_list}"
    )
    assert edge.dashed == dashed, (
        f"エッジ '{from_h}'→'{to_h}' dashed: 実際={edge.dashed} 期待={dashed}"
    )


def assert_edge_coords(
    layout: GridLayout,
    from_lane: int,
    from_row: int,
    to_lane: int,
    to_row: int,
    dashed: bool,
) -> None:
    """グリッド座標でエッジを探してアサートする（joint/dummy 経由用）。"""
    edge = next(
        (
            e
            for e in layout.edges
            if (
                e.from_lane == from_lane
                and e.from_row == from_row
                and e.to_lane == to_lane
                and e.to_row == to_row
            )
        ),
        None,
    )
    edge_list = [(e.from_lane, e.from_row, e.to_lane, e.to_row) for e in layout.edges]
    assert edge is not None, (
        f"エッジ ({from_lane},{from_row})→({to_lane},{to_row}) が見つからない。edges={edge_list}"
    )
    assert edge.dashed == dashed, (
        f"エッジ ({from_lane},{from_row})→({to_lane},{to_row}) "
        f"dashed: 実際={edge.dashed} 期待={dashed}"
    )
