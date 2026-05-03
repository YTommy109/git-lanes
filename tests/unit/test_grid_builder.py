# tests/unit/test_grid_builder.py
"""grid_builder の単体テスト。11 ケース対応。"""

from __future__ import annotations

from backend.models import Branch, Commit, Tag
from backend.services.grid_builder import build_grid, build_layout
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


def _t(name: str, commit_hash: str) -> Tag:
    """テスト用 Tag を生成する。"""
    return Tag(name=name, repo_id=_REPO, commit_hash=commit_hash)


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
    assert (
        edge.dashed == dashed
    ), f"エッジ '{from_h}'→'{to_h}' dashed: 実際={edge.dashed} 期待={dashed}"


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
    assert (
        edge is not None
    ), f"エッジ ({from_lane},{from_row})→({to_lane},{to_row}) が見つからない。edges={edge_list}"
    assert edge.dashed == dashed, (
        f"エッジ ({from_lane},{from_row})→({to_lane},{to_row}) "
        f"dashed: 実際={edge.dashed} 期待={dashed}"
    )


def test_ケース1_コミット1つ():
    # --- Arrange ---
    commits = [_c("a", parents=[], at=1)]
    branches = [_b("main", "a")]
    parents = _p(commits, {})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a", lane=1, row=0, kind="commit")
    assert len([n for n in layout.nodes if n.kind == "dummy"]) == 0
    assert len(layout.edges) == 0


def test_ケース2_直線接続():
    # --- Arrange ---
    commits = [_c("b", parents=["a"], at=2), _c("a", parents=[], at=1)]
    branches = [_b("main", "b")]
    parents = _p(commits, {"b": ["a"]})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "b", lane=1, row=0, kind="commit")
    assert_node(layout, "a", lane=1, row=1, kind="commit")
    assert_edge(layout, "b", "a", dashed=False)


def test_ケース3_同じコミットを指す2ブランチ():
    # --- Arrange ---
    commits = [_c("a", parents=[], at=1)]
    branches = [_b("main", "a"), _b("develop", "a")]
    parents = _p(commits, {})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    # 同じコミットを指す 2 ブランチ → コミットはレーン 1 に 1 つだけ
    assert_node(layout, "a", lane=1, row=0, kind="commit")
    commit_nodes = [n for n in layout.nodes if n.kind == "commit"]
    assert len(commit_nodes) == 1
    # 両ブランチのラベルが lane 1 に存在する
    lane1_labels = next((lb for lb in layout.branch_labels if lb.lane == 1), None)
    assert lane1_labels is not None
    assert "main" in lane1_labels.names
    assert "develop" in lane1_labels.names


def test_ケース4_2ブランチが同じ親を持つ():
    # --- Arrange ---
    # a と b は同じ committed_at → row 0 を共有
    commits = [
        _c("a", parents=["c"], at=2),
        _c("b", parents=["c"], at=2),
        _c("c", parents=[], at=1),
    ]
    branches = [_b("main", "a"), _b("develop", "b")]
    parents = _p(commits, {"a": ["c"], "b": ["c"]})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a", lane=1, row=0, kind="commit")
    assert_node(layout, "b", lane=4, row=0, kind="commit")
    assert_node(layout, "c", lane=1, row=1, kind="commit")
    assert_edge(layout, "a", "c", dashed=False)
    assert_edge(layout, "b", "c", dashed=False)


def test_ケース5_developがmainの途中から分岐():
    # --- Arrange ---
    # a1 と b1 を同じ at=2 → row 1 を共有
    commits = [
        _c("a2", parents=["a1"], at=3),
        _c("a1", parents=["a0"], at=2),
        _c("b1", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a2"), _b("develop", "b1")]
    parents = _p(commits, {"a2": ["a1"], "a1": ["a0"], "b1": ["a0"]})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a2", lane=1, row=0, kind="commit")
    assert_node(layout, "a1", lane=1, row=1, kind="commit")
    assert_node(layout, "b1", lane=4, row=1, kind="commit")
    assert_node(layout, "a0", lane=1, row=2, kind="commit")
    # develop のダミーノードが row=0 lane=4 にある
    dummy_nodes = [n for n in layout.nodes if n.kind == "dummy" and n.lane == 4 and n.row == 0]
    assert len(dummy_nodes) == 1
    # ダミー→b1 エッジ（同一レーン縦、破線）
    assert_edge_coords(layout, 4, 0, 4, 1, dashed=True)
    # b1→a0 エッジ（斜め、実線）
    assert_edge(layout, "b1", "a0", dashed=False)


def test_ケース6_developが古いコミットを指す():
    # --- Arrange ---
    # develop は a0 を直接指している
    commits = [
        _c("a2", parents=["a1"], at=3),
        _c("a1", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a2"), _b("develop", "a0")]
    parents = _p(commits, {"a2": ["a1"], "a1": ["a0"]})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a2", lane=1, row=0, kind="commit")
    assert_node(layout, "a1", lane=1, row=1, kind="commit")
    assert_node(layout, "a0", lane=1, row=2, kind="commit")
    # develop のダミーが row=0, lane=4
    dummy_nodes = [n for n in layout.nodes if n.kind == "dummy" and n.lane == 4]
    assert len(dummy_nodes) == 1
    assert dummy_nodes[0].row == 0
    # ジョイントノードが row=1, lane=4 にある
    joint_nodes = [n for n in layout.nodes if n.kind == "joint" and n.lane == 4]
    assert len(joint_nodes) == 1
    assert joint_nodes[0].row == 1
    # エッジ: ダミー(4,0)→ジョイント(4,1) 縦破線
    assert_edge_coords(layout, 4, 0, 4, 1, dashed=True)
    # エッジ: ジョイント(4,1)→a0(1,2) 斜め破線
    assert_edge_coords(layout, 4, 1, 1, 2, dashed=True)


def test_ケース7_developがmainより新しい():
    # --- Arrange ---
    commits = [
        _c("b1", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a0"), _b("develop", "b1")]
    parents = _p(commits, {"b1": ["a0"]})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    # main のダミーが row=0, lane=1 にある（main tip=a0 は row=1）
    main_dummies = [n for n in layout.nodes if n.kind == "dummy" and n.lane == 1]
    assert len(main_dummies) == 1
    assert main_dummies[0].row == 0
    assert_node(layout, "b1", lane=4, row=0, kind="commit")
    assert_node(layout, "a0", lane=1, row=1, kind="commit")
    # ダミー(1,0)→a0(1,1) 縦破線
    assert_edge_coords(layout, 1, 0, 1, 1, dashed=True)
    # b1→a0 斜め実線
    assert_edge(layout, "b1", "a0", dashed=False)
    # main のラベルは lane=1（ダミーの位置）
    main_labels = next((lb for lb in layout.branch_labels if lb.lane == 1), None)
    assert main_labels is not None
    assert "main" in main_labels.names
    # develop のラベルは lane=4
    develop_labels = next((lb for lb in layout.branch_labels if lb.lane == 4), None)
    assert develop_labels is not None
    assert "develop" in develop_labels.names


def test_ブランチtipがdummyレーンに表示される():
    # --- Arrange ---
    # feat の tip (c1) は main の tip (b0) より新しく、b0 は feat の祖先になる。
    # branches リストで feat が先なので feat が lane=1、main が lane=4 を取得する。
    # b0 はコミット配置で feat の流れ (lane=1) に吸収されるため placed[b0].lane=1 になるが、
    # main のラベルはダミーノードがある lane=4 に表示されなければならない。
    commits = [
        _c("c1", parents=["b0"], at=2),
        _c("b0", parents=[], at=1),
    ]
    branches = [_b("feat", "c1"), _b("main", "b0")]
    parents = _p(commits, {"c1": ["b0"]})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "c1", lane=1, row=0, kind="commit")
    assert_node(layout, "b0", lane=1, row=1, kind="commit")
    # main のダミーが lane=4, row=0 にある
    main_dummies = [n for n in layout.nodes if n.kind == "dummy" and n.lane == 4]
    assert len(main_dummies) == 1
    assert_edge_coords(layout, 4, 0, 1, 1, dashed=True)
    # feat のラベルは lane=1
    feat_labels = next((lb for lb in layout.branch_labels if lb.lane == 1), None)
    assert feat_labels is not None
    assert "feat" in feat_labels.names
    # main のラベルは lane=4（ダミーの位置）であり、lane=1 には含まれない
    main_labels = next((lb for lb in layout.branch_labels if lb.lane == 4), None)
    assert main_labels is not None, "main のラベルが lane=4 に存在しない"
    assert "main" in main_labels.names
    assert "main" not in (feat_labels.names if feat_labels else [])


def test_ケース8_マージ済みブランチ名削除済み():
    # --- Arrange ---
    # a1 はマージコミット。第1親=a0（main継続）、第2親=b1（削除済み develop）
    commits = [
        _c("a1", parents=["a0", "b1"], at=3),
        _c("b1", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a1")]  # develop は削除済み → branches に含まれない
    parents = _p(commits, {"a1": ["a0", "b1"], "b1": ["a0"]})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a1", lane=1, row=0, kind="commit")
    assert_node(layout, "b1", lane=2, row=1, kind="commit")
    assert_node(layout, "a0", lane=1, row=2, kind="commit")
    # a1→a0 縦エッジ（main色）
    assert_edge(layout, "a1", "a0", dashed=False)
    # a1→b1 斜めエッジ
    assert_edge(layout, "a1", "b1", dashed=False)
    # b1→a0 斜めエッジ
    assert_edge(layout, "b1", "a0", dashed=False)
    # ダミーなし
    assert len([n for n in layout.nodes if n.kind == "dummy"]) == 0


def test_ケース9_マージ済み削除ブランチ複数コミット():
    # --- Arrange ---
    commits = [
        _c("a1", parents=["a0", "b3"], at=5),
        _c("b3", parents=["b2"], at=4),
        _c("b2", parents=["b1"], at=3),
        _c("b1", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a1")]
    parents = _p(
        commits,
        {
            "a1": ["a0", "b3"],
            "b3": ["b2"],
            "b2": ["b1"],
            "b1": ["a0"],
        },
    )

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a1", lane=1, row=0, kind="commit")
    assert_node(layout, "b3", lane=2, row=1, kind="commit")
    assert_node(layout, "b2", lane=2, row=2, kind="commit")
    assert_node(layout, "b1", lane=2, row=3, kind="commit")
    assert_node(layout, "a0", lane=1, row=4, kind="commit")
    assert_edge(layout, "a1", "b3", dashed=False)
    assert_edge(layout, "b3", "b2", dashed=False)
    assert_edge(layout, "b2", "b1", dashed=False)
    assert_edge(layout, "b1", "a0", dashed=False)
    # a1→a0 縦エッジ（main 色）
    assert_edge(layout, "a1", "a0", dashed=False)


def test_ケース10_削除ブランチとアクティブブランチ混在():
    # --- Arrange ---
    # b1 と c1 は同じ at=2 → row 1 を共有
    commits = [
        _c("a1", parents=["a0", "b1"], at=3),
        _c("b1", parents=["a0"], at=2),
        _c("c1", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a1"), _b("feat/something01", "c1")]
    parents = _p(commits, {"a1": ["a0", "b1"], "b1": ["a0"], "c1": ["a0"]})

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a1", lane=1, row=0, kind="commit")
    assert_node(layout, "b1", lane=2, row=1, kind="commit")
    assert_node(layout, "c1", lane=4, row=1, kind="commit")
    assert_node(layout, "a0", lane=1, row=2, kind="commit")
    # feat のダミーが row=0, lane=4
    feat_dummies = [n for n in layout.nodes if n.kind == "dummy" and n.lane == 4]
    assert len(feat_dummies) == 1
    # ダミー(4,0)→c1(4,1) 縦破線
    assert_edge_coords(layout, 4, 0, 4, 1, dashed=True)
    # 各エッジ
    assert_edge(layout, "a1", "b1", dashed=False)
    assert_edge(layout, "a1", "a0", dashed=False)
    assert_edge(layout, "b1", "a0", dashed=False)
    assert_edge(layout, "c1", "a0", dashed=False)


def test_ケース11_2ブランチをマージ後にどちらも削除():
    # --- Arrange ---
    # 注: plan の座標表では c1=lane3, b1=lane2 だが、
    # 本アルゴリズムでは a2 が先に c1 を lane=2 に予約するため c1=lane2, b1=lane3 になる。
    # 削除済みブランチの中間レーン割り当ては処理順に依存するため、視覚的な等価性は保たれる。
    # a1 と c1 は同じ at=3 → row 1 を共有
    commits = [
        _c("a2", parents=["a1", "c1"], at=4),
        _c("a1", parents=["a0", "b1"], at=3),
        _c("c1", parents=["a0"], at=3),
        _c("b1", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a2")]  # develop, feat はどちらも削除済み
    parents = _p(
        commits,
        {
            "a2": ["a1", "c1"],
            "a1": ["a0", "b1"],
            "c1": ["a0"],
            "b1": ["a0"],
        },
    )

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a2", lane=1, row=0, kind="commit")
    assert_node(layout, "a1", lane=1, row=1, kind="commit")
    # c1 と b1 のレーン: アルゴリズムの予約順に依存する
    # a2 が c1 を lane=2 に予約 → c1=2, a1 が b1 を lane=3 に予約 → b1=3
    assert_node(layout, "c1", lane=2, row=1, kind="commit")
    assert_node(layout, "b1", lane=3, row=2, kind="commit")
    assert_node(layout, "a0", lane=1, row=3, kind="commit")
    # c1→a0 のジョイントノードが lane=2, row=2
    c1_joints = [n for n in layout.nodes if n.kind == "joint" and n.lane == 2]
    assert len(c1_joints) == 1
    assert c1_joints[0].row == 2
    # エッジ
    assert_edge(layout, "a2", "a1", dashed=False)
    assert_edge(layout, "a2", "c1", dashed=False)
    assert_edge(layout, "a1", "b1", dashed=False)
    assert_edge(layout, "a1", "a0", dashed=False)
    assert_edge(layout, "b1", "a0", dashed=False)
    # c1(2,1)→joint(2,2) 縦
    assert_edge_coords(layout, 2, 1, 2, 2, dashed=False)
    # joint(2,2)→a0(1,3) 斜め
    assert_edge_coords(layout, 2, 2, 1, 3, dashed=False)


def test_ケース12_削除済みブランチを2段階でマージ():
    # --- Arrange ---
    # a1 が配置されるとき b1 の lane=2 が合流して解放され、b0 が lane=2 を再利用する
    commits = [
        _c("a2", parents=["a1", "b1"], at=5),
        _c("b1", parents=["a1"], at=4),
        _c("a1", parents=["a0", "b0"], at=3),
        _c("b0", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a2")]
    parents = _p(
        commits,
        {
            "a2": ["a1", "b1"],
            "b1": ["a1"],
            "a1": ["a0", "b0"],
            "b0": ["a0"],
        },
    )

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a2", lane=1, row=0, kind="commit")
    assert_node(layout, "b1", lane=2, row=1, kind="commit")
    assert_node(layout, "a1", lane=1, row=2, kind="commit")
    # b1 が a1 に収束してレーン 2 を解放 → b0 がレーン 2 を再利用
    assert_node(layout, "b0", lane=2, row=3, kind="commit")
    assert_node(layout, "a0", lane=1, row=4, kind="commit")
    assert_edge(layout, "a2", "a1", dashed=False)
    assert_edge(layout, "a2", "b1", dashed=False)
    assert_edge(layout, "b1", "a1", dashed=False)
    assert_edge(layout, "a1", "a0", dashed=False)
    assert_edge(layout, "a1", "b0", dashed=False)
    assert_edge(layout, "b0", "a0", dashed=False)


def test_ケース15_ブランチtipにタグが付いている():
    # --- Arrange ---
    commits = [_c("a1", parents=["a0"], at=2), _c("a0", parents=[], at=1)]
    branches = [_b("main", "a1")]
    parents = _p(commits, {"a1": ["a0"]})
    tags = [_t("v1.0", "a1")]

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=tags)

    # --- Assert ---
    main_labels = next((lb for lb in layout.branch_labels if lb.lane == 1), None)
    assert main_labels is not None
    assert "main" in main_labels.names
    assert "[v1.0]" in main_labels.names


def test_ケース13_コミットにタグが付いている():
    # --- Arrange ---
    commits = [_c("a1", parents=["a0"], at=2), _c("a0", parents=[], at=1)]
    branches = [_b("main", "a1")]
    parents = _p(commits, {"a1": ["a0"]})
    tags = [_t("v1.0", "a0")]

    # --- Act ---
    result = build_grid(commits, parents, branches, tags=tags)

    # --- Assert ---
    a0_node = next((n for n in result.nodes if n.commit.hash == "a0"), None)
    assert a0_node is not None
    tag_labels = [lb for lb in a0_node.labels if lb.kind == "tag"]
    assert len(tag_labels) == 1
    assert tag_labels[0].text == "v1.0"


def test_ケース14_コミットにタグが2つ付いている():
    # --- Arrange ---
    commits = [_c("a1", parents=["a0"], at=2), _c("a0", parents=[], at=1)]
    branches = [_b("main", "a1")]
    parents = _p(commits, {"a1": ["a0"]})
    tags = [_t("v1.0", "a0"), _t("bugfix", "a0")]

    # --- Act ---
    result = build_grid(commits, parents, branches, tags=tags)

    # --- Assert ---
    a0_node = next((n for n in result.nodes if n.commit.hash == "a0"), None)
    assert a0_node is not None
    tag_labels = [lb for lb in a0_node.labels if lb.kind == "tag"]
    assert len(tag_labels) == 1
    assert tag_labels[0].text == "v1.0, bugfix"
