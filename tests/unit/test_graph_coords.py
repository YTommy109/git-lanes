# tests/unit/test_graph_coords.py
"""graph_coords の単体テスト。"""

from backend.models import Branch, Commit
from backend.services.graph_builder import build_graph
from backend.services.graph_coords import (
    _make_svg_node,
    _resolve_node_type,
    assign_coords,
)
from backend.services.graph_models import (
    MARGIN_TOP,
    SPACING_Y,
    GraphBranch,
    GraphLayer,
    GraphLine,
    GraphNode,
)

_REPO_ID = "test-repo"


def make_commit(prefix: str) -> Commit:
    """テスト用 Commit をハッシュプレフィックスから生成する。"""
    h = prefix * 40
    return Commit(
        hash=h[:40],
        short_hash=h[:7],
        message="msg",
        author_name="a",
        author_email="a@b.c",
        committed_at=1,
        repo_id=_REPO_ID,
    )


def make_line() -> GraphLine:
    """テスト用 GraphLine を生成する。"""
    branch = GraphBranch(color="#aaa")
    return GraphLine(branch=branch, color="#aaa")


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


def _make_layer(index: int, count: int) -> GraphLayer:
    """ノードを count 個持つ GraphLayer を生成する。"""
    layer = GraphLayer(index=index)
    for i in range(count):
        branch = GraphBranch(color="#aaa")
        line = GraphLine(branch=branch, color="#aaa")
        node = GraphNode(
            commit=_c(chr(ord("a") + i), i + 1),
            layer=layer,
            primary_line=line,
        )
        layer.nodes.append(node)
    return layer


def test_assign_coords_yはindex_に応じて計算される():
    # --- Arrange ---
    layer = _make_layer(index=2, count=1)

    # --- Act ---
    assign_coords([layer])

    # --- Assert ---
    assert layer.y == MARGIN_TOP + 2 * SPACING_Y


def test_assign_coords_同一レイヤーのxは単調増加():
    # --- Arrange ---
    layer = _make_layer(index=0, count=3)

    # --- Act ---
    assign_coords([layer])

    # --- Assert ---
    xs = [n.x for n in layer.nodes]
    assert xs == sorted(xs)
    assert len(set(xs)) == 3


def test_assign_coords_ライン継続性でxが引き継がれる():
    # --- Arrange ---
    branch = GraphBranch(color="#aaa")
    line = GraphLine(branch=branch, color="#aaa")
    layer0 = GraphLayer(index=0)
    layer1 = GraphLayer(index=1)
    node0 = GraphNode(commit=_c("a", 1), layer=layer0, primary_line=line)
    node1 = GraphNode(commit=_c("b", 2), layer=layer1, primary_line=line)
    layer0.nodes.append(node0)
    layer1.nodes.append(node1)

    # --- Act ---
    assign_coords([layer0, layer1])

    # --- Assert ---
    assert node0.x == node1.x  # 同じラインは同じ X を維持


def test_build_graph_ノードのcxcyが正の値():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [Branch(name="main", repo_id=_REPO_ID, tip_hash="b" * 40, is_remote=0)]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    for n in result.nodes:
        assert n.cx > 0
        assert n.cy > 0


def test_build_graph_エッジのd属性が有効なSVGパス():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [Branch(name="main", repo_id=_REPO_ID, tip_hash="b" * 40, is_remote=0)]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    assert len(result.edges) == 1
    assert result.edges[0].d.startswith("M ")
    assert " L " in result.edges[0].d


def test_build_graph_マージ第2親のエッジが描画される():
    # --- Arrange ---
    # main: M(merge) → B → A、第 2 親: F → A
    m, b, a, f = (_c("m", 4), _c("b", 3), _c("a", 1), _c("f", 2))
    commits = [m, b, f, a]
    parents = {
        "m" * 40: ["b" * 40, "f" * 40],
        "b" * 40: ["a" * 40],
        "f" * 40: ["a" * 40],
    }
    branches = [Branch(name="main", repo_id=_REPO_ID, tip_hash="m" * 40, is_remote=0)]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    # M→F のエッジが存在する（第 2 親チェーンのエッジ）
    node_by_hash = {n.commit.hash: n for n in result.nodes}
    assert "f" * 40 in node_by_hash
    # M の cx は F の cx と異なる（別レーンに配置される）
    assert node_by_hash["m" * 40].cx != node_by_hash["f" * 40].cx


def test_resolve_node_type_layer0実ノードはtip():
    """Layer 0 の実ノード（dummy=False）は "tip" を返す。"""
    # --- Arrange ---
    layer = GraphLayer(index=0)
    node = GraphNode(commit=make_commit("a"), layer=layer, primary_line=make_line(), dummy=False)
    # --- Act ---
    result = _resolve_node_type(node, layer, parents={})
    # --- Assert ---
    assert result == "tip"


def test_resolve_node_type_親なしはroot():
    """親コミットが存在しないノードは "root" を返す。"""
    # --- Arrange ---
    layer = GraphLayer(index=1)
    node = GraphNode(commit=make_commit("b"), layer=layer, primary_line=make_line(), dummy=False)
    # --- Act ---
    result = _resolve_node_type(node, layer, parents={})
    # --- Assert ---
    assert result == "root"


def test_resolve_node_type_親2つ以上はmerge():
    """親コミットが 2 つ以上のノードは "merge" を返す。"""
    # --- Arrange ---
    layer = GraphLayer(index=2)
    node = GraphNode(commit=make_commit("c"), layer=layer, primary_line=make_line(), dummy=False)
    parents = {"c" * 40: ["d" * 40, "e" * 40]}
    # --- Act ---
    result = _resolve_node_type(node, layer, parents=parents)
    # --- Assert ---
    assert result == "merge"


def test_resolve_node_type_通常ノードはregular():
    """親が 1 つのノードは "regular" を返す。"""
    # --- Arrange ---
    layer = GraphLayer(index=1)
    node = GraphNode(commit=make_commit("f"), layer=layer, primary_line=make_line(), dummy=False)
    parents = {"f" * 40: ["g" * 40]}
    # --- Act ---
    result = _resolve_node_type(node, layer, parents=parents)
    # --- Assert ---
    assert result == "regular"


def test_make_svg_node_node_typeが設定される():
    """_make_svg_node が SvgNode.node_type を正しく設定する。"""
    # --- Arrange ---
    layer = GraphLayer(index=0)
    node = GraphNode(commit=make_commit("h"), layer=layer, primary_line=make_line(), dummy=False)
    node.x = 30.0
    # --- Act ---
    svg_node = _make_svg_node(node, layer, parents={}, labels={})
    # --- Assert ---
    assert svg_node.node_type == "tip"


def test_assign_coords_配置済みラインのxが衝突するとき右にずらす():
    """primary_line.positioned=True で x が last_x 以下のとき last_x+1 に補正する（line 32）。"""
    # --- Arrange ---
    line_a = make_line()
    line_b = make_line()
    # line_b は既に x=0.0 に positioned 済みとしておく（後から同一レイヤーに入ると衝突）
    line_b.x = 0.0
    line_b.positioned = True

    layer = GraphLayer(index=0)
    node_a = GraphNode(commit=make_commit("a"), layer=layer, primary_line=line_a)
    node_b = GraphNode(commit=make_commit("b"), layer=layer, primary_line=line_b)
    layer.nodes.extend([node_a, node_b])

    # --- Act ---
    assign_coords([layer])

    # --- Assert ---
    assert node_b.x > node_a.x, "衝突時は右にずれるべき"


def test_build_graph_親が不明なコミットはエッジをスキップする():
    """親が commit_to_node に存在しない場合エッジが生成されない（graph_coords.py line 96）。"""
    # --- Arrange ---: commit_a の親は存在しないコミット
    a = make_commit("a")
    parents = {"a" * 40: ["z" * 40]}  # "z" は commits に含まれない
    branches = [Branch(name="main", repo_id="test", tip_hash="a" * 40, is_remote=0)]

    # --- Act ---
    result = build_graph([a], parents, branches, [])

    # --- Assert ---
    assert result.edges == [], "存在しない親へのエッジは生成されないべき"
