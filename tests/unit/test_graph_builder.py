# tests/unit/test_graph_builder.py
"""graph_builder の単体テスト。"""

from backend.models import Branch, Commit
from backend.services.graph_builder import _build_children_map, _is_ready, build_graph
from backend.services.graph_models import GraphBranch, GraphLayer, GraphLine, GraphNode

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
