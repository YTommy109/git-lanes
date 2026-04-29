# グラフ描画アルゴリズム全面書き換え 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gitup の GIGraph アルゴリズムを Python で再実装し、マージ済みブランチを含むすべてのコミットを正確に描画する

**Architecture:** TIP→根方向のボトムアップ層状構築でダミーノードを使いながらマージ第2親チェーンを別ラインとして展開する。エッジは `(child_hash, parent_hash) → color` の辞書で管理し、ダミーチェーン解決後に実ノード間のみ描画する。git→SQLite パイプラインは変更しない。

**Tech Stack:** Python 3.12 / FastAPI / SQLModel / Jinja2 / pytest

---

## ファイル構成

### 新規作成
- `backend/services/graph_models.py` — データ構造（GraphBranch/GraphLine/GraphNode/GraphLayer/SvgNode/SvgEdge/GraphResult）
- `backend/services/graph_builder.py` — Phase 1〜3 アルゴリズム + `build_graph()` 公開関数
- `backend/services/graph_coords.py` — Phase 4 座標計算 + SVG 変換
- `tests/unit/test_graph_builder.py` — Phase 1〜3 の単体テスト
- `tests/unit/test_graph_coords.py` — Phase 4 + SVG 変換の単体テスト

### 更新
- `backend/repositories/cache_repo.py` — `list_all_commits()` を追加
- `backend/routers/html.py` — `graph_builder.build_graph()` を呼ぶよう差し替え
- `backend/templates/graph.html` — SvgNode/SvgEdge の新形式に対応

### 削除（Task 8 で実行）
- `backend/services/graph_layout.py`
- `backend/services/lane_assignment.py`
- `backend/services/lane_nodes.py`
- `backend/services/topo_sort.py`
- `tests/unit/test_graph_layout.py`

---

## Task 1: graph_models.py — データ構造の定義

**Files:**
- Create: `backend/services/graph_models.py`

- [ ] **Step 1: ファイルを作成する**

```python
# backend/services/graph_models.py
"""グラフ描画のデータモデル。"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.models import Commit

LANE_COLORS: list[str] = [
    "#4a9cf6", "#f6974a", "#4af690", "#f64a7b",
    "#af4af6", "#f6e44a", "#4af6f0", "#f6a84a",
]
SPACING_X: float = 30.0
SPACING_Y: float = 60.0
MARGIN_TOP: float = 30.0


@dataclass
class GraphBranch:
    """論理的なブランチ/レーン。"""

    color: str
    refs: list[str] = field(default_factory=list)
    main_line: GraphLine | None = None
    tip_node: GraphNode | None = None


@dataclass
class GraphLine:
    """ブランチの流れを表すラインセグメント。X 座標をレイヤー間で引き継ぐ。"""

    branch: GraphBranch
    color: str
    is_main: bool = False
    nodes: list[GraphNode] = field(default_factory=list)
    x: float = 0.0
    positioned: bool = False


@dataclass
class GraphNode:
    """個々のコミット。dummy=True は子未確定のプレースホルダー。"""

    commit: Commit
    layer: GraphLayer
    primary_line: GraphLine
    dummy: bool = False
    x: float = 0.0
    parent_nodes: list[GraphNode] = field(default_factory=list)


@dataclass
class GraphLayer:
    """時系列の 1 段（Y 座標単位）。"""

    index: int
    nodes: list[GraphNode] = field(default_factory=list)
    y: float = 0.0


@dataclass
class SvgNode:
    """SVG テンプレートへ渡すノード情報。"""

    cx: float
    cy: float
    color: str
    commit: Commit
    labels: list[str]


@dataclass
class SvgEdge:
    """SVG テンプレートへ渡すエッジ情報。"""

    d: str
    color: str


@dataclass
class GraphResult:
    """build_graph() の返り値。"""

    nodes: list[SvgNode]
    edges: list[SvgEdge]
    canvas_width: float
    canvas_height: float
```

- [ ] **Step 2: インポートが通ることを確認する**

```bash
uv run python -c "from backend.services.graph_models import GraphResult; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add backend/services/graph_models.py
git commit -m "feat: グラフ描画のデータモデルを追加する"
```

---

## Task 2: graph_builder.py — アルゴリズムのテストを書いて実装する

**Files:**
- Create: `tests/unit/test_graph_builder.py`
- Create: `backend/services/graph_coords.py`（スタブ）
- Create: `backend/services/graph_builder.py`

- [ ] **Step 1: テストファイルを作成する**

```python
# tests/unit/test_graph_builder.py
"""graph_builder の単体テスト。"""
from backend.models import Branch, Commit, Tag
from backend.services.graph_builder import _build_children_map, _is_ready, build_graph
from backend.services.graph_models import GraphBranch, GraphLayer, GraphLine, GraphNode

_REPO_ID = "test-repo"


def _c(prefix: str, at: int) -> Commit:
    """テスト用 Commit を生成する。"""
    h = prefix * 40
    return Commit(
        hash=h, short_hash=h[:7], message="msg",
        author_name="a", author_email="a@b.c",
        committed_at=at, repo_id=_REPO_ID,
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
    assert "main" in tip_node.labels
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py
```

Expected: `ImportError` または `ModuleNotFoundError`

- [ ] **Step 3: graph_coords.py のスタブを作成する**（graph_builder が import するため先に作る）

```python
# backend/services/graph_coords.py
"""Phase 4: 座標計算と SVG 変換。"""
from __future__ import annotations

from backend.services.graph_models import GraphLayer, GraphNode, GraphResult


def assign_coords(layers: list[GraphLayer]) -> None:
    """各ノードの x/y 座標をインプレースで付与する。"""
    pass  # Task 3 で実装


def to_svg(
    layers: list[GraphLayer],
    parents: dict[str, list[str]],
    commit_to_node: dict[str, GraphNode],
    edge_colors: dict[tuple[str, str], str],
    labels_by_hash: dict[str, list[str]],
) -> GraphResult:
    """座標付きレイヤーを SvgNode/SvgEdge に変換して GraphResult を返す。"""
    return GraphResult(nodes=[], edges=[], canvas_width=300.0, canvas_height=100.0)
```

- [ ] **Step 4: graph_builder.py を実装する**

```python
# backend/services/graph_builder.py
"""gitup GIGraph アルゴリズムの Python 実装。"""
from __future__ import annotations

from backend.models import Branch, Commit, Tag
from backend.services.graph_coords import assign_coords, to_svg
from backend.services.graph_models import (
    LANE_COLORS, GraphBranch, GraphLayer, GraphLine, GraphNode, GraphResult,
)


def _build_children_map(parents: dict[str, list[str]]) -> dict[str, list[str]]:
    """parents dict から {parent_hash: [child_hash]} の逆引き辞書を構築する。"""
    children: dict[str, list[str]] = {}
    for child, plist in parents.items():
        for p in plist:
            children.setdefault(p, []).append(child)
    return children


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
            commit=tip, layer=layer, primary_line=line,
            dummy=not _is_ready(tip.hash, layer, commit_to_node, children_map),
        )
        branch.tip_node = node
        line.nodes.append(node)
        layer.nodes.append(node)
        commit_to_node[tip.hash] = node


def _build_layers(
    layer0: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
) -> tuple[list[GraphLayer], dict[tuple[str, str], str]]:
    """Phase 3: 前レイヤーを処理して次レイヤーを生成するループを繰り返す。

    Returns:
        (layers, edge_colors): edge_colors は (child_hash, parent_hash) → 線の色。
    """
    layers = [layer0]
    edge_colors: dict[tuple[str, str], str] = {}
    prev = layer0

    while True:
        curr = GraphLayer(index=len(layers))

        for node in prev.nodes:
            if node.dummy:
                ready = _is_ready(node.commit.hash, curr, commit_to_node, children_map)
                new = GraphNode(
                    commit=node.commit, layer=curr,
                    primary_line=node.primary_line, dummy=not ready,
                )
                node.primary_line.nodes.append(new)
                curr.nodes.append(new)
                commit_to_node[node.commit.hash] = new
            else:
                for i, ph in enumerate(parents.get(node.commit.hash, [])):
                    if i == 0:
                        line = node.primary_line
                    else:
                        color = LANE_COLORS[color_idx[0] % len(LANE_COLORS)]
                        color_idx[0] += 1
                        branch = GraphBranch(color=color)
                        line = GraphLine(branch=branch, color=color)
                        branch.main_line = line
                        line.nodes.append(node)

                    edge_colors[(node.commit.hash, ph)] = line.color

                    if ph in commit_to_node:
                        line.nodes.append(commit_to_node[ph])
                    elif ph in commit_map:
                        ready = _is_ready(ph, curr, commit_to_node, children_map)
                        pnode = GraphNode(
                            commit=commit_map[ph], layer=curr,
                            primary_line=line, dummy=not ready,
                        )
                        line.nodes.append(pnode)
                        curr.nodes.append(pnode)
                        commit_to_node[ph] = pnode

        if not curr.nodes:
            break
        layers.append(curr)
        prev = curr

    return layers, edge_colors


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

    labels: dict[str, list[str]] = {}
    if head_hash:
        labels.setdefault(head_hash, []).insert(0, "HEAD")
    for b in branches:
        labels.setdefault(b.tip_hash, []).append(b.name)
    for t in tags:
        labels.setdefault(t.commit_hash, []).append(t.name)

    tips = _collect_tips(commit_map, branches, tags, head_hash)
    if not tips:
        return GraphResult(nodes=[], edges=[], canvas_width=300.0, canvas_height=100.0)

    layer0 = GraphLayer(index=0)
    commit_to_node: dict[str, GraphNode] = {}
    color_idx = [0]
    _build_layer0(tips, layer0, commit_to_node, children_map, labels, color_idx)

    layers, edge_colors = _build_layers(
        layer0, commit_to_node, children_map, parents, commit_map, color_idx
    )
    assign_coords(layers)
    return to_svg(layers, parents, commit_to_node, edge_colors, labels)
```

- [ ] **Step 5: テストを実行して _build_children_map / _is_ready は PASS し build_graph は FAIL することを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py
```

Expected: `test_build_children_map_*` と `test_is_ready_*` は PASS、`test_build_graph_*` は FAIL（`to_svg` がスタブで nodes=[]）

- [ ] **Step 6: コミット**

```bash
git add backend/services/graph_builder.py backend/services/graph_coords.py tests/unit/test_graph_builder.py
git commit -m "feat: graph_builder のアルゴリズム骨格を追加する"
```

---

## Task 3: graph_coords.py — 座標計算と SVG 変換のテストを書いて実装する

**Files:**
- Create: `tests/unit/test_graph_coords.py`
- Modify: `backend/services/graph_coords.py`（スタブを実装に置き換え）

- [ ] **Step 1: テストファイルを作成する**

```python
# tests/unit/test_graph_coords.py
"""graph_coords の単体テスト。"""
from backend.models import Branch, Commit
from backend.services.graph_builder import build_graph
from backend.services.graph_coords import assign_coords
from backend.services.graph_models import (
    MARGIN_TOP, SPACING_X, SPACING_Y,
    GraphBranch, GraphLayer, GraphLine, GraphNode,
)

_REPO_ID = "test-repo"


def _c(prefix: str, at: int) -> Commit:
    """テスト用 Commit を生成する。"""
    h = prefix * 40
    return Commit(
        hash=h, short_hash=h[:7], message="msg",
        author_name="a", author_email="a@b.c",
        committed_at=at, repo_id=_REPO_ID,
    )


def _make_layer(index: int, count: int) -> GraphLayer:
    """ノードを count 個持つ GraphLayer を生成する。"""
    layer = GraphLayer(index=index)
    for i in range(count):
        branch = GraphBranch(color="#aaa")
        line = GraphLine(branch=branch, color="#aaa")
        node = GraphNode(commit=_c(chr(ord("a") + i), i + 1), layer=layer, primary_line=line)
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
    edge_pairs = {(e.d.split()[1] + "," + e.d.split()[2]) for e in result.edges}
    node_by_hash = {n.commit.hash: n for n in result.nodes}
    assert "f" * 40 in node_by_hash
    # M の cx は F の cx と異なる（別レーンに配置される）
    assert node_by_hash["m" * 40].cx != node_by_hash["f" * 40].cx
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run task test tests/unit/test_graph_coords.py
```

Expected: `assign_coords` のテストは FAIL（スタブ）

- [ ] **Step 3: graph_coords.py を実装する**

```python
# backend/services/graph_coords.py
"""Phase 4: 座標計算と SVG 変換。"""
from __future__ import annotations

from backend.services.graph_models import (
    GraphLayer, GraphNode, GraphResult, SvgEdge, SvgNode,
    MARGIN_TOP, SPACING_X, SPACING_Y,
)


def assign_coords(layers: list[GraphLayer]) -> None:
    """各ノードの x/y 座標をインプレースで付与する。同一ラインの x は引き継がれる。"""
    for layer in layers:
        layer.y = MARGIN_TOP + layer.index * SPACING_Y
        last_x = 0.0
        for node in layer.nodes:
            if node.primary_line.positioned:
                x = node.primary_line.x
                if x <= last_x:
                    x = last_x + 1.0
            else:
                x = last_x + 1.0
            node.x = x
            node.primary_line.x = x
            node.primary_line.positioned = True
            last_x = x


def to_svg(
    layers: list[GraphLayer],
    parents: dict[str, list[str]],
    commit_to_node: dict[str, GraphNode],
    edge_colors: dict[tuple[str, str], str],
    labels_by_hash: dict[str, list[str]],
) -> GraphResult:
    """座標付きレイヤーを SvgNode/SvgEdge に変換して GraphResult を返す。

    エッジは commit_to_node の最終状態（ダミー解決済み）を参照して描画する。
    """
    svg_nodes: list[SvgNode] = []
    svg_edges: list[SvgEdge] = []

    for layer in layers:
        for node in layer.nodes:
            if node.dummy:
                continue
            svg_nodes.append(SvgNode(
                cx=node.x * SPACING_X,
                cy=layer.y,
                color=node.primary_line.color,
                commit=node.commit,
                labels=labels_by_hash.get(node.commit.hash, []),
            ))
            for parent_hash in parents.get(node.commit.hash, []):
                parent_node = commit_to_node.get(parent_hash)
                if parent_node is None or parent_node.dummy:
                    continue
                color = edge_colors.get((node.commit.hash, parent_hash), node.primary_line.color)
                x1, y1 = node.x * SPACING_X, layer.y
                x2, y2 = parent_node.x * SPACING_X, parent_node.layer.y
                svg_edges.append(SvgEdge(
                    d=f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}",
                    color=color,
                ))

    max_cx = max((n.cx for n in svg_nodes), default=0.0)
    max_cy = max((n.cy for n in svg_nodes), default=0.0)
    return GraphResult(
        nodes=svg_nodes,
        edges=svg_edges,
        canvas_width=max_cx + 150.0,
        canvas_height=max_cy + 80.0,
    )
```

- [ ] **Step 4: テストをすべて実行して PASS することを確認する**

```bash
uv run task test tests/unit/test_graph_coords.py tests/unit/test_graph_builder.py
```

Expected: すべて PASS

- [ ] **Step 5: コミット**

```bash
git add backend/services/graph_coords.py tests/unit/test_graph_coords.py
git commit -m "feat: Phase 4 座標計算と SVG 変換を実装する"
```

---

## Task 4: cache_repo.py — list_all_commits を追加する

**Files:**
- Modify: `backend/repositories/cache_repo.py`

- [ ] **Step 1: `list_recent_commits` の直後（57 行目付近）に `list_all_commits` を追加する**

```python
def list_all_commits(session: Session, repo_id: str) -> list[Commit]:
    """コミットを committed_at 降順で全件返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        コミットのリスト。新しい順に並ぶ。
    """
    return list(
        session.exec(
            select(Commit)
            .where(Commit.repo_id == repo_id)
            .order_by(Commit.committed_at.desc())  # type: ignore[union-attr]
        ).all()
    )
```

- [ ] **Step 2: インポートが通ることを確認する**

```bash
uv run python -c "from backend.repositories.cache_repo import list_all_commits; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add backend/repositories/cache_repo.py
git commit -m "feat: cache_repo に list_all_commits を追加する"
```

---

## Task 5: html.py — graph_builder を呼ぶよう差し替える

**Files:**
- Modify: `backend/routers/html.py`

- [ ] **Step 1: ファイル全体を書き換える**

```python
# backend/routers/html.py
"""HTML 応答（htmx 向け）。"""

from __future__ import annotations

from pathlib import Path

import pygit2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from backend.db import get_session
from backend.models import Repository
from backend.repositories import cache_repo
from backend.services import graph_builder, sync_service
from backend.validation import parse_commit_hash, parse_repo_id

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["html"])


@router.get("/", response_class=HTMLResponse)
async def welcome(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ウェルカム画面を返す。"""
    repos = cache_repo.list_repositories(session)
    return templates.TemplateResponse(
        request, "welcome.html", {"repos": repos, "current_repo_id": None}
    )


@router.get("/repos/{repo_id}/graph", response_class=HTMLResponse)
async def graph_page(
    request: Request,
    repo_id: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ブランチグラフ画面を返す。"""
    rid = parse_repo_id(repo_id)
    rec = cache_repo.get_repository(session, rid)
    if rec is None:
        raise HTTPException(status_code=404, detail="リポジトリが見つかりません")
    try:
        sync_service.sync_repository(session, rid, rec.path)
    except pygit2.GitError as exc:
        raise HTTPException(status_code=400, detail="Git リポジトリを開けません") from exc
    rows = cache_repo.list_all_commits(session, rid)
    parents = cache_repo.parents_by_child(session, [r.hash for r in rows])
    branches = cache_repo.list_branches(session, rid)
    tags = cache_repo.list_tags(session, rid)
    result = graph_builder.build_graph(rows, parents, branches, tags, rec.cached_head)
    context: dict = {
        "repo_id": rid,
        "repo_name": rec.name,
        "nodes": result.nodes,
        "edges": result.edges,
        "svg_width": result.canvas_width,
        "svg_height": result.canvas_height,
        "repos": cache_repo.list_repositories(session),
        "current_repo_id": rid,
    }
    return templates.TemplateResponse(request, "graph.html", context)


@router.get(
    "/repos/{repo_id}/commits/{commit_hash}/detail",
    response_class=HTMLResponse,
)
async def commit_detail(
    request: Request,
    repo_id: str,
    commit_hash: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """コミット詳細の HTML 断片を返す（htmx 用）。"""
    rid = parse_repo_id(repo_id)
    ch = parse_commit_hash(commit_hash)
    row = cache_repo.get_commit(session, rid, ch)
    if row is None:
        raise HTTPException(status_code=404, detail="コミットが見つかりません")
    tags = cache_repo.get_tags_for_commit(session, rid, ch)
    return templates.TemplateResponse(
        request, "partials/detail.html", {"commit": row, "tags": tags}
    )
```

- [ ] **Step 2: lint と型チェックを通す**

```bash
uv run task lint && uv run task typecheck
```

Expected: エラーなし

- [ ] **Step 3: コミット**

```bash
git add backend/routers/html.py
git commit -m "feat: html.py を graph_builder.build_graph に切り替える"
```

---

## Task 6: graph.html — SvgNode/SvgEdge の新形式に対応する

**Files:**
- Modify: `backend/templates/graph.html`

- [ ] **Step 1: ファイル全体を書き換える**

```html
{% extends "base.html" %}
{% block title %}{{ repo_name }} — グラフ{% endblock %}
{% block body %}
<div
  hx-ext="sse"
  sse-connect="/repos/{{ repo_id }}/events"
  _="on sse:reload call window.location.reload()"
></div>
<div id="commit-tooltip"
     style="display:none;position:fixed;background:#222;color:#eee;padding:4px 10px;border-radius:4px;font-size:12px;pointer-events:none;z-index:1000;max-width:320px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"></div>
<main class="l--flex" style="height: 100%">
  <section class="-p:20 -ov:auto -bgc:white" aria-label="コミットグラフ"
           style="flex: 2; border-right: 1px solid var(--divider)">
    <header>
      <h1>{{ repo_name }}</h1>
    </header>
    {% if not nodes %}
      <p>コミットがありません。</p>
    {% else %}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="100%"
        height="{{ svg_height }}"
        viewBox="0 0 {{ svg_width }} {{ svg_height }}"
        role="img"
        aria-label="コミット履歴"
      >
        {# エッジ（コミット間の接続線） #}
        {% for edge in edges %}
          <path
            d="{{ edge.d }}"
            stroke="{{ edge.color }}"
            stroke-width="2.5"
            fill="none"
          />
        {% endfor %}

        {# コミット円とラベル #}
        {% for node in nodes %}
          <g
            class="commit-node"
            data-msg="{{ node.commit.message.split('\n')[0] }}"
            hx-get="/repos/{{ repo_id }}/commits/{{ node.commit.hash }}/detail"
            hx-target="#commit-detail"
            hx-swap="innerHTML"
            _="on mouseenter set #commit-tooltip.textContent to my @data-msg
                             then set #commit-tooltip.style.display to 'block'
                             then set #commit-tooltip.style.top to (event.clientY - 36) + 'px'
                             then set #commit-tooltip.style.left to (event.clientX + 12) + 'px'
               on mouseleave set #commit-tooltip.style.display to 'none'
               on click remove .selected from .commit-node then add .selected to me"
          >
            <circle cx="{{ node.cx }}" cy="{{ node.cy }}" r="8" fill="{{ node.color }}"/>
            {% if node.labels %}
              <text
                x="{{ node.cx + 14 }}"
                y="{{ node.cy + 4 }}"
                font-size="10"
                fill="{{ node.color }}"
                font-weight="bold"
                pointer-events="none"
              >{{ node.labels | join(", ") }}</text>
            {% endif %}
          </g>
        {% endfor %}
      </svg>
    {% endif %}
  </section>
  <aside class="-p:20 -bgc:base-2 -fx:1" style="min-width: 18rem" aria-label="コミット詳細">
    <h2>詳細</h2>
    <div id="commit-detail">
      <p class="-c:text-2">コミットを選択してください。</p>
    </div>
  </aside>
</main>
{% endblock %}
```

- [ ] **Step 2: 開発サーバーを起動してブラウザで確認する**

```bash
uv run task dev
```

`http://localhost:8000` を開き、登録済みリポジトリのグラフ画面で以下を確認する:
- コミット円が表示される
- ブランチラベルが TIP コミットの横に表示される
- マージコミットの両側（第 1 親・第 2 親）のラインが別色で描画される

- [ ] **Step 3: コミット**

```bash
git add backend/templates/graph.html
git commit -m "feat: graph.html を SvgNode/SvgEdge の新形式に対応する"
```

---

## Task 7: 全品質チェックを通す

**Files:**
- なし（既存テストの修正のみ）

- [ ] **Step 1: テストスイート全体を実行する**

```bash
uv run task test
```

`test_graph_layout.py` がエラーになる場合は次のステップで削除する（Task 8 を先に実行する）。

- [ ] **Step 2: lint・型チェックを通す**

```bash
uv run task lint && uv run task typecheck
```

エラーがあれば根本原因を確認して修正する。

- [ ] **Step 3: コミット（修正があれば）**

```bash
git add -p
git commit -m "fix: 型チェック・lint エラーを修正する"
```

---

## Task 8: 旧ファイルを削除する

**Files:**
- Delete: `backend/services/graph_layout.py`
- Delete: `backend/services/lane_assignment.py`
- Delete: `backend/services/lane_nodes.py`
- Delete: `backend/services/topo_sort.py`
- Delete: `tests/unit/test_graph_layout.py`

- [ ] **Step 1: 旧ファイルを削除する**

```bash
git rm backend/services/graph_layout.py \
       backend/services/lane_assignment.py \
       backend/services/lane_nodes.py \
       backend/services/topo_sort.py \
       tests/unit/test_graph_layout.py
```

- [ ] **Step 2: 残留参照がないことを確認する**

```bash
grep -r "graph_layout\|lane_assignment\|lane_nodes\|topo_sort" backend/ tests/ --include="*.py"
```

残っていれば修正する。

- [ ] **Step 3: 全品質チェックを通す**

```bash
uv run task test && uv run task lint && uv run task typecheck
```

Expected: すべて PASS / エラーなし

- [ ] **Step 4: コミット**

```bash
git commit -m "refactor: 旧グラフレイアウトモジュールを削除する"
```

---

## 完了条件

- [ ] `uv run task test` がすべて PASS
- [ ] `uv run task lint` がエラーなし
- [ ] `uv run task typecheck` がエラーなし
- [ ] アプリを起動してマージコミットの第 2 親チェーンが別色のラインで描画されていること（目視確認）
