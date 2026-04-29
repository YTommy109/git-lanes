# tests/unit/test_graph_builder.py
"""graph_builder の単体テスト。"""

from backend.models import Branch, Commit, Tag
from backend.services.graph_builder import _build_children_map, _is_ready, build_graph
from backend.services.graph_builder_helpers import (
    _apply_overlap_avoidance,
    _make_branch_headers,
    _realize_dummy,
)
from backend.services.graph_models import (
    GraphBranch,
    GraphLayer,
    GraphLine,
    GraphNode,
    SvgBranchHeader,
    SvgLabel,
)

_REPO_ID = "test-repo"


def _c(prefix: str, at: int) -> Commit:
    """テスト用 Commit を生成する。"""
    h = prefix * 40
    return Commit(
        hash=h,
        short_hash=h[:7],
        message="msg",
        author_name="a",
        author_email="a@b.c",
        committed_at=at,
        repo_id=_REPO_ID,
    )


def _b(name: str, tip: str, remote: int = 0) -> Branch:
    """テスト用 Branch を生成する。"""
    return Branch(name=name, repo_id=_REPO_ID, tip_hash=tip * 40, is_remote=remote)


def test_build_children_map_単方向エッジ():
    # --- Arrange ---
    parents = {"b" * 40: ["a" * 40]}

    # --- Act ---
    result = _build_children_map(parents)

    # --- Assert ---
    assert result == {"a" * 40: ["b" * 40]}


def test_build_children_map_マージコミット():
    # --- Arrange ---
    parents = {"m" * 40: ["a" * 40, "b" * 40]}

    # --- Act ---
    result = _build_children_map(parents)

    # --- Assert ---
    assert "m" * 40 in result["a" * 40]
    assert "m" * 40 in result["b" * 40]


def test_is_ready_子なしコミットはTrue():
    # --- Arrange ---
    layer = GraphLayer(index=0)

    # --- Act / Assert ---
    assert _is_ready("a" * 40, layer, {}, {}) is True


def test_is_ready_子が別レイヤーに確定済みならTrue():
    # --- Arrange ---
    layer0 = GraphLayer(index=0)
    layer1 = GraphLayer(index=1)
    branch = GraphBranch(color="#fff")
    line = GraphLine(branch=branch, color="#fff")
    child_node = GraphNode(commit=_c("b", 2), layer=layer0, primary_line=line, dummy=False)
    commit_to_node = {"b" * 40: child_node}
    children_map = {"a" * 40: ["b" * 40]}

    # --- Act / Assert ---
    assert _is_ready("a" * 40, layer1, commit_to_node, children_map) is True


def test_is_ready_子がダミーならFalse():
    # --- Arrange ---
    layer = GraphLayer(index=0)
    branch = GraphBranch(color="#fff")
    line = GraphLine(branch=branch, color="#fff")
    child_node = GraphNode(commit=_c("b", 2), layer=layer, primary_line=line, dummy=True)
    commit_to_node = {"b" * 40: child_node}
    children_map = {"a" * 40: ["b" * 40]}

    # --- Act / Assert ---
    assert _is_ready("a" * 40, layer, commit_to_node, children_map) is False


def test_is_ready_子が同レイヤーにいるならFalse():
    # --- Arrange ---
    layer = GraphLayer(index=0)
    branch = GraphBranch(color="#fff")
    line = GraphLine(branch=branch, color="#fff")
    child_node = GraphNode(commit=_c("b", 2), layer=layer, primary_line=line, dummy=False)
    commit_to_node = {"b" * 40: child_node}
    children_map = {"a" * 40: ["b" * 40]}

    # --- Act / Assert ---
    assert _is_ready("a" * 40, layer, commit_to_node, children_map) is False


def test_build_graph_直線履歴():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_b("main", "b")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    hashes = {n.commit.hash for n in result.nodes}
    assert "b" * 40 in hashes
    assert "a" * 40 in hashes
    assert len(result.edges) == 1


def test_build_graph_マージコミットの第2親チェーンが表示される():
    # --- Arrange ---
    # main: M(merge) → B → A
    # feat: F → A（F が M の第 2 親）
    m, b, a, f = _c("m", 4), _c("b", 3), _c("a", 1), _c("f", 2)
    commits = [m, b, f, a]
    parents = {
        "m" * 40: ["b" * 40, "f" * 40],
        "b" * 40: ["a" * 40],
        "f" * 40: ["a" * 40],
    }
    branches = [_b("main", "m")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    hashes = {n.commit.hash for n in result.nodes}
    assert "f" * 40 in hashes  # 第 2 親チェーンのコミットが描画される
    assert "m" * 40 in hashes
    assert "b" * 40 in hashes
    assert "a" * 40 in hashes


def test_build_graph_空データは空を返す():
    # --- Act ---
    result = build_graph([], {}, [], [])

    # --- Assert ---
    assert result.nodes == []
    assert result.edges == []


def test_build_graph_ブランチラベルがTIPノードに付く():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_b("main", "b")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    tip_node = next(n for n in result.nodes if n.commit.hash == "b" * 40)
    assert any(lbl.text == "main" for lbl in tip_node.labels)


def test_build_graph_ブランチラベルがSvgLabelで返る():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_b("main", "b")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    tip_node = next(n for n in result.nodes if n.commit.hash == "b" * 40)
    assert any(lbl.text == "main" and lbl.kind == "branch" for lbl in tip_node.labels)


def test_build_graph_HEADラベルのkindはhead():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_b("main", "b")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [], head_hash="b" * 40)

    # --- Assert ---
    tip_node = next(n for n in result.nodes if n.commit.hash == "b" * 40)
    assert any(lbl.text == "HEAD" and lbl.kind == "head" for lbl in tip_node.labels)


def test_build_graph_HEADブランチのエッジにis_mainがつく():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_b("main", "b")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [], head_hash="b" * 40)

    # --- Assert ---
    assert any(e.is_main for e in result.edges)


def test_build_graph_非HEADブランチエッジのis_mainはFalse():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_b("main", "b")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])  # head_hash なし

    # --- Assert ---
    assert all(not e.is_main for e in result.edges)


def test_build_graph_共通祖先コミットの重複がない():
    """
    A → D → X
    B → X
    というグラフで X が重複ノードを持たないことを検証する。
    （旧実装では dummy_X と _place_parent の衝突で X が 2 つ生成された）
    """
    # --- Arrange ---
    a, b, d, x = _c("a", 4), _c("b", 3), _c("d", 2), _c("x", 1)
    commits = [a, b, d, x]
    # A → D → X、B → X
    parents = {
        "a" * 40: ["d" * 40],
        "b" * 40: ["x" * 40],
        "d" * 40: ["x" * 40],
    }
    branches = [_b("main", "a"), _b("feat", "b")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    hashes = [n.commit.hash for n in result.nodes]
    assert hashes.count("x" * 40) == 1, "コミット X が重複している"
    assert len({n.commit.hash for n in result.nodes}) == len(result.nodes), "重複ノードが存在する"


def test_build_graph_ダイアモンドマージでエッジ数が正しい():
    """
    M → [B, F]
    B → A
    F → A
    という構造でエッジが M→B, M→F, B→A, F→A の 4 本だけであることを検証する。
    重複ノードがあると A へのエッジが余分に生成される。
    """
    # --- Arrange ---
    m, b, f, a = _c("m", 4), _c("b", 3), _c("f", 2), _c("a", 1)
    commits = [m, b, f, a]
    parents = {
        "m" * 40: ["b" * 40, "f" * 40],
        "b" * 40: ["a" * 40],
        "f" * 40: ["a" * 40],
    }
    branches = [_b("main", "m")]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    assert len(result.nodes) == 4, f"ノード数が異常: {len(result.nodes)}"
    hashes = {n.commit.hash for n in result.nodes}
    assert "a" * 40 in hashes, "共通祖先 A が欠落している"
    a_node = next(n for n in result.nodes if n.commit.hash == "a" * 40)
    edges_to_a = [e for e in result.edges if f"{a_node.cx:.1f} {a_node.cy:.1f}" in e.d]
    assert len(edges_to_a) == 2, f"A へのエッジ数が異常: {len(edges_to_a)}"


def _make_line(color: str = "#fff") -> GraphLine:
    branch = GraphBranch(color=color)
    line = GraphLine(branch=branch, color=color)
    branch.main_line = line
    return line


def test_realize_dummy_先に実ノードが同レイヤーに配置済みなら再利用する():
    """_realize_dummy の early-return パスを検証する（line 67-68）。"""
    # --- Arrange ---
    commit = _c("a", 1)
    layer = GraphLayer(index=0)
    line = _make_line()
    real_node = GraphNode(commit=commit, layer=layer, primary_line=line, dummy=False)
    layer.nodes.append(real_node)
    commit_to_node = {commit.hash: real_node}

    dummy_line = _make_line()
    prev_layer = GraphLayer(index=1)
    dummy_node = GraphNode(commit=commit, layer=prev_layer, primary_line=dummy_line, dummy=True)

    # --- Act ---
    _realize_dummy(dummy_node, layer, commit_to_node, {})

    # --- Assert ---
    assert real_node in dummy_line.nodes, "既存実ノードが dummy_line に追加されるべき"
    assert commit_to_node[commit.hash] is real_node, "commit_to_node は変更されないべき"


def test_apply_overlap_avoidance_長いテキストを切り詰める():
    """ヘッダーテキストが隣接ヘッダーと重なるとき切り詰める（line 91）。"""
    # --- Arrange ---
    headers = [
        SvgBranchHeader(cx=0.0, cy=0.0, labels=[], color="#000", display_text="a" * 30),
        SvgBranchHeader(cx=20.0, cy=0.0, labels=[], color="#000", display_text="b"),
    ]

    # --- Act ---
    _apply_overlap_avoidance(headers, char_width_px=6.5, gap_px=6.0)

    # --- Assert ---
    assert headers[0].display_text.endswith("…"), "切り詰めが行われるべき"
    assert len(headers[0].display_text) < 30, "元のテキストより短くなるべき"


def test_make_branch_headers_空レイヤーは空リストを返す():
    """layers が空のとき [] を返す（line 104）。"""
    # --- Arrange / Act ---
    result = _make_branch_headers([], {})

    # --- Assert ---
    assert result == []


def test_make_branch_headers_ラベルなしノードはスキップする():
    """Layer 0 にラベルがないノードはヘッダーに含まれない（line 118）。"""
    # --- Arrange ---
    commit = _c("a", 1)
    layer = GraphLayer(index=0)
    line = _make_line()
    node = GraphNode(commit=commit, layer=layer, primary_line=line)
    layer.nodes.append(node)

    # --- Act ---
    result = _make_branch_headers([layer], {})  # labels_by_hash は空

    # --- Assert ---
    assert result == []


def test_make_branch_headers_ダミーtipにコネクター座標を付与する():
    """ダミー tip に対して connector_to_x/y が設定される（line 126-129）。"""
    # --- Arrange ---
    commit = _c("a", 1)
    layer0 = GraphLayer(index=0)
    layer1 = GraphLayer(index=1)
    layer1.y = 60.0

    line = _make_line()
    dummy_node = GraphNode(commit=commit, layer=layer0, primary_line=line, dummy=True)
    dummy_node.x = 0.0
    layer0.nodes.append(dummy_node)

    real_node = GraphNode(commit=commit, layer=layer1, primary_line=line, dummy=False)
    real_node.x = 2.0
    layer1.nodes.append(real_node)

    labels = {commit.hash: [SvgLabel(text="main", kind="branch")]}

    # --- Act ---
    result = _make_branch_headers([layer0, layer1], labels)

    # --- Assert ---
    assert len(result) == 1
    h = result[0]
    assert h.connector_to_x is not None, "コネクター X 座標が設定されるべき"
    assert h.connector_to_y == 60.0, "コネクター Y 座標が layer1.y と一致するべき"


def test_build_graph_リモートブランチはダミーtipのコネクターを生成する():
    """
    リモートブランチの tip が main の祖先の場合、
    branch_headers にコネクター付きエントリが含まれる。
    """
    # --- Arrange ---
    b, a = _c("b", 2), _c("a", 1)
    commits = [b, a]
    parents = {"b" * 40: ["a" * 40]}
    branches = [
        _b("main", "b"),
        _b("origin/main", "a", remote=1),
    ]

    # --- Act ---
    result = build_graph(commits, parents, branches, [], head_hash="b" * 40)

    # --- Assert ---
    connector_headers = [h for h in result.branch_headers if h.connector_to_y is not None]
    assert len(connector_headers) >= 1, "コネクター付きヘッダーが少なくとも 1 つ存在するべき"


def _t(name: str, tip: str) -> Tag:
    """テスト用 Tag を生成する。"""
    return Tag(name=name, repo_id=_REPO_ID, commit_hash=tip * 40)


def test_build_graph_タグがブランチヘッダーに表示される():
    """Tag を渡すと tag kind ラベルが付く（graph_builder.py 52, 68 行）。"""
    # --- Arrange ---
    b, a = _c("b", 2), _c("a", 1)
    commits = [b, a]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_b("main", "b")]
    tags = [_t("v1.0", "a")]

    # --- Act ---
    result = build_graph(commits, parents, branches, tags)

    # --- Assert ---
    a_node = next(n for n in result.nodes if n.commit.hash == "a" * 40)
    assert any(lbl.kind == "tag" and lbl.text == "v1.0" for lbl in a_node.labels)


def test_build_graph_コミットがあるがブランチなしはノードなし():
    """branches/tags/head が全て無効なら tips が空になり空結果を返す（graph_builder.py 121 行）。"""
    # --- Arrange ---
    a = _c("a", 1)
    commits = [a]
    parents = {}
    branches = [_b("main", "z")]  # "z" * 40 は commit_map に存在しない

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    assert result.nodes == []
    assert result.edges == []
