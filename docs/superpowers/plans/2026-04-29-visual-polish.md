# コミットグラフ ビジュアル改善 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** コミットグラフのノード種別区別・メインライン強調・バッジラベルを実装して GitUp に近い洗練された見た目にする。

**Architecture:** Python 側（graph_models / graph_builder / graph_coords）はデータ属性を追加し、Jinja2 テンプレート側で条件分岐描画する。エッジ形状は直線のまま維持。

**Tech Stack:** Python 3.12, FastAPI, Jinja2, pytest, SVG

---

## ファイル構成

| ファイル | 役割・変更内容 |
|----------|--------------|
| `backend/services/graph_models.py` | `NodeType`・`LabelKind`・`SvgLabel` 型追加。`SvgNode.node_type`・`SvgEdge.is_main`・`GraphLine.is_head_branch` 追加。`SvgNode.labels` を `list[SvgLabel]` に変更 |
| `backend/services/graph_builder_helpers.py` | **新規作成**。`_is_ready`・`_place_parent`・`_realize_dummy` を phases から分離。`_place_parent` に `edge_is_main` dict 構築を追加 |
| `backend/services/graph_builder_phases.py` | helpers から 3 関数を削除し import に変更。`edge_is_main` を全関数シグネチャに追加。`build_layers` 返り値に `edge_is_main` を追加 |
| `backend/services/graph_builder.py` | `_build_labels` 返り値を `list[SvgLabel]` に変更。`_build_layer0` に `head_hash` を追加して HEAD フラグをセット。`build_graph` の `build_layers` アンパックと `to_svg` 呼び出しを更新 |
| `backend/services/graph_coords.py` | `_resolve_node_type` 新設。`_make_svg_node`・`_make_svg_edges`・`to_svg` を更新 |
| `backend/templates/graph.html` | ノード種別描画・バッジラベル・エッジ太さの条件分岐に更新 |
| `tests/unit/test_graph_builder.py` | `labels` アクセスを `SvgLabel` 対応に修正。HEAD フラグ・is_main のテストを追加 |
| `tests/unit/test_graph_coords.py` | `_resolve_node_type`・`is_main` エッジのテストを追加 |

**タスク依存関係の注意**: 各タスク完了後にテスト全体がパスすること。Task 3 は phases・coords・builder の 3 ファイルをまとめて更新するため、途中でテストが壊れる状態を作らない。

---

## Task 1: データモデル拡張（graph_models.py）

**Files:**
- Modify: `backend/services/graph_models.py`

- [ ] **Step 1: `graph_models.py` を以下の内容に置き換える**

```python
# backend/services/graph_models.py
"""グラフ描画のデータモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from backend.models import Commit

LANE_COLORS: list[str] = [
    "#4a9cf6",
    "#f6974a",
    "#4af690",
    "#f64a7b",
    "#af4af6",
    "#f6e44a",
    "#4af6f0",
    "#f6a84a",
]
SPACING_X: float = 30.0
SPACING_Y: float = 60.0
MARGIN_TOP: float = 30.0

NodeType = Literal["tip", "root", "merge", "regular"]
LabelKind = Literal["head", "branch", "tag"]


@dataclass
class SvgLabel:
    """ブランチ名・タグ・HEAD ラベルの種別付きデータ。"""

    text: str
    kind: LabelKind


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
    is_head_branch: bool = False
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
    labels: list[SvgLabel]
    node_type: NodeType = "regular"


@dataclass
class SvgEdge:
    """SVG テンプレートへ渡すエッジ情報。"""

    d: str
    color: str
    is_main: bool = False


@dataclass
class GraphResult:
    """build_graph() の返り値。"""

    nodes: list[SvgNode]
    edges: list[SvgEdge]
    canvas_width: float
    canvas_height: float
```

- [ ] **Step 2: インポートエラーがないことを確認する**

```bash
uv run python -c "from backend.services.graph_models import SvgNode, SvgEdge, SvgLabel, NodeType, LabelKind; print('OK')"
```

期待出力: `OK`

- [ ] **Step 3: コミット**

```bash
git add backend/services/graph_models.py
git commit -m "feat: グラフモデルに NodeType・SvgLabel・is_head_branch を追加する"
```

---

## Task 2: graph_builder_helpers.py を新規作成する

150 行制約のため `graph_builder_phases.py` から低レベルヘルパーを分離する。
このタスクでは phases.py は変更しない（まだ helpers.py を import しない）。

**Files:**
- Create: `backend/services/graph_builder_helpers.py`

- [ ] **Step 1: テストが現在パスしていることを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py -v
```

期待出力: 全テスト PASSED

- [ ] **Step 2: `graph_builder_helpers.py` を作成する**

```python
# backend/services/graph_builder_helpers.py
"""graph_builder_phases の低レベルヘルパー関数。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_models import (
    GraphLayer,
    GraphLine,
    GraphNode,
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
```

- [ ] **Step 3: インポートエラーがないことを確認する**

```bash
uv run python -c "from backend.services.graph_builder_helpers import _is_ready, _place_parent, _realize_dummy; print('OK')"
```

期待出力: `OK`

- [ ] **Step 4: コミット**

```bash
git add backend/services/graph_builder_helpers.py
git commit -m "refactor: graph_builder_helpers.py を新規作成し低レベルヘルパーを分離する"
```

---

## Task 3: phases・coords・builder の配線を一括更新する

**テストを壊さないために 3 ファイルをまとめて更新してコミットする。**

変更内容:
- `graph_builder_phases.py`: helpers を import し `edge_is_main` を追加
- `graph_coords.py`: `to_svg` に `edge_is_main` 引数を追加（`_make_svg_edges` 内では未使用のままで OK）
- `graph_builder.py`: `build_layers` の返り値をアンパック、`to_svg` 呼び出しを更新

**Files:**
- Modify: `backend/services/graph_builder_phases.py`
- Modify: `backend/services/graph_coords.py`
- Modify: `backend/services/graph_builder.py`

- [ ] **Step 1: 現在のテストがパスしていることを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py tests/unit/test_graph_coords.py -v
```

期待出力: 全テスト PASSED

- [ ] **Step 2: `graph_builder_phases.py` を以下の内容に置き換える**

```python
# backend/services/graph_builder_phases.py
"""Phase 2〜3: レイヤー構築の実装。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_builder_helpers import (
    _is_ready,
    _place_parent,
    _realize_dummy,
)
from backend.services.graph_models import (
    LANE_COLORS,
    GraphBranch,
    GraphLayer,
    GraphLine,
    GraphNode,
)


def _process_ready_node(
    node: GraphNode,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
) -> None:
    """確定済みノードの親をカレントレイヤーに配置する。"""
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
        _place_parent(
            ph, line, node, curr, commit_to_node, children_map, commit_map,
            edge_colors, edge_is_main,
        )


def _process_layer(
    prev: GraphLayer,
    curr: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
) -> None:
    """prev の各ノードを評価して curr にノードを追加する。"""
    for node in prev.nodes:
        if node.dummy:
            _realize_dummy(node, curr, commit_to_node, children_map)
        else:
            _process_ready_node(
                node, curr, commit_to_node, children_map, parents,
                commit_map, color_idx, edge_colors, edge_is_main,
            )


def build_layers(
    layer0: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    parents: dict[str, list[str]],
    commit_map: dict[str, Commit],
    color_idx: list[int],
) -> tuple[list[GraphLayer], dict[tuple[str, str], str], dict[tuple[str, str], bool]]:
    """Phase 3: 前レイヤーを処理して次レイヤーを生成するループを繰り返す。

    Returns:
        (layers, edge_colors, edge_is_main):
            edge_colors は (child_hash, parent_hash) → 線の色。
            edge_is_main は (child_hash, parent_hash) → HEAD ブランチのラインか。
    """
    layers = [layer0]
    edge_colors: dict[tuple[str, str], str] = {}
    edge_is_main: dict[tuple[str, str], bool] = {}
    prev = layer0
    while True:
        curr = GraphLayer(index=len(layers))
        _process_layer(
            prev, curr, commit_to_node, children_map, parents,
            commit_map, color_idx, edge_colors, edge_is_main,
        )
        if not curr.nodes:
            break
        layers.append(curr)
        prev = curr
    return layers, edge_colors, edge_is_main
```

- [ ] **Step 3: `graph_coords.py` の `to_svg` に `edge_is_main` 引数を追加する**

`to_svg` 関数のシグネチャと内部 `_make_svg_edges` 呼び出しを更新する（`_make_svg_edges` 自体の実装は Task 5 で変更）。

`graph_coords.py` 全体を以下に置き換える:

```python
# backend/services/graph_coords.py
"""Phase 4: 座標計算と SVG 変換。"""

from __future__ import annotations

from backend.services.graph_models import (
    MARGIN_TOP,
    SPACING_X,
    SPACING_Y,
    GraphLayer,
    GraphNode,
    GraphResult,
    SvgEdge,
    SvgLabel,
    SvgNode,
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


def _make_svg_node(
    node: GraphNode,
    layer: GraphLayer,
    labels_by_hash: dict[str, list[SvgLabel]],
) -> SvgNode:
    """単一ノードの SvgNode を生成する。"""
    return SvgNode(
        cx=node.x * SPACING_X,
        cy=layer.y,
        color=node.primary_line.color,
        commit=node.commit,
        labels=labels_by_hash.get(node.commit.hash, []),
    )


def _make_svg_edges(
    node: GraphNode,
    layer: GraphLayer,
    parents: dict[str, list[str]],
    commit_to_node: dict[str, GraphNode],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
) -> list[SvgEdge]:
    """単一ノードから親へのエッジリストを生成する。ダミー親はスキップする。"""
    edges: list[SvgEdge] = []
    for ph in parents.get(node.commit.hash, []):
        pnode = commit_to_node.get(ph)
        if pnode is None or pnode.dummy:
            continue
        color = edge_colors.get((node.commit.hash, ph), node.primary_line.color)
        is_main = edge_is_main.get((node.commit.hash, ph), False)
        x1, y1 = node.x * SPACING_X, layer.y
        x2, y2 = pnode.x * SPACING_X, pnode.layer.y
        edges.append(
            SvgEdge(d=f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}", color=color, is_main=is_main)
        )
    return edges


def to_svg(
    layers: list[GraphLayer],
    parents: dict[str, list[str]],
    commit_to_node: dict[str, GraphNode],
    edge_colors: dict[tuple[str, str], str],
    edge_is_main: dict[tuple[str, str], bool],
    labels_by_hash: dict[str, list[SvgLabel]],
) -> GraphResult:
    """座標付きレイヤーを SvgNode/SvgEdge に変換して GraphResult を返す。"""
    svg_nodes: list[SvgNode] = []
    svg_edges: list[SvgEdge] = []
    for layer in layers:
        for node in layer.nodes:
            if node.dummy:
                continue
            svg_nodes.append(_make_svg_node(node, layer, labels_by_hash))
            svg_edges.extend(
                _make_svg_edges(node, layer, parents, commit_to_node, edge_colors, edge_is_main)
            )
    max_cx = max((n.cx for n in svg_nodes), default=0.0)
    max_cy = max((n.cy for n in svg_nodes), default=0.0)
    return GraphResult(
        nodes=svg_nodes,
        edges=svg_edges,
        canvas_width=max_cx + 150.0,
        canvas_height=max_cy + 80.0,
    )
```

- [ ] **Step 4: `graph_builder.py` を更新して `build_layers` の 3 値アンパックと `to_svg` 呼び出しを修正する**

`graph_builder.py` の import 部分を変更する。

変更前:
```python
from backend.services.graph_builder_phases import (
    _is_ready,  # noqa: F401  テストから graph_builder 経由でアクセスされる
    build_layers,
)
```

変更後:
```python
from backend.services.graph_builder_helpers import (
    _is_ready,  # noqa: F401  テストから graph_builder 経由でアクセスされる
)
from backend.services.graph_builder_phases import build_layers
```

`build_graph` 内の `build_layers` アンパックと `to_svg` 呼び出しを変更する。

変更前:
```python
    layers, edge_colors = build_layers(
        layer0, commit_to_node, children_map, parents, commit_map, color_idx
    )
    assign_coords(layers)
    return to_svg(layers, parents, commit_to_node, edge_colors, labels)
```

変更後:
```python
    layers, edge_colors, edge_is_main = build_layers(
        layer0, commit_to_node, children_map, parents, commit_map, color_idx
    )
    assign_coords(layers)
    return to_svg(layers, parents, commit_to_node, edge_colors, edge_is_main, labels)
```

- [ ] **Step 5: テストがパスすることを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py tests/unit/test_graph_coords.py -v
```

期待出力: 全テスト PASSED

- [ ] **Step 6: コミット**

```bash
git add backend/services/graph_builder_phases.py backend/services/graph_coords.py backend/services/graph_builder.py
git commit -m "refactor: phases・coords・builder の配線を edge_is_main 対応に一括更新する"
```

---

## Task 4: `_build_labels` の SvgLabel 化と HEAD ブランチフラグ

**Files:**
- Modify: `backend/services/graph_builder.py`
- Modify: `tests/unit/test_graph_builder.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/unit/test_graph_builder.py` の末尾に追加する:

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py::test_build_graph_ブランチラベルがSvgLabelで返る -v
```

期待出力: FAILED

- [ ] **Step 3: 既存テストを SvgLabel 対応に修正する**

`tests/unit/test_graph_builder.py` の `test_build_graph_ブランチラベルがTIPノードに付く` を変更する。

変更前:
```python
    assert "main" in tip_node.labels
```

変更後:
```python
    assert any(lbl.text == "main" for lbl in tip_node.labels)
```

- [ ] **Step 4: `graph_builder.py` の `_build_labels` を SvgLabel 対応に変更する**

import に `SvgLabel` を追加する。

変更前（import 部分）:
```python
from backend.services.graph_models import (
    LANE_COLORS,
    GraphBranch,
    GraphLayer,
    GraphLine,
    GraphNode,
    GraphResult,
)
```

変更後:
```python
from backend.services.graph_models import (
    LANE_COLORS,
    GraphBranch,
    GraphLayer,
    GraphLine,
    GraphNode,
    GraphResult,
    SvgLabel,
)
```

`_build_labels` 関数を以下に置き換える:

```python
def _build_labels(
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None,
) -> dict[str, list[SvgLabel]]:
    """ブランチ・タグ・HEAD のラベル辞書を構築する。"""
    labels: dict[str, list[SvgLabel]] = {}
    if head_hash:
        labels.setdefault(head_hash, []).insert(0, SvgLabel(text="HEAD", kind="head"))
    for b in branches:
        labels.setdefault(b.tip_hash, []).append(SvgLabel(text=b.name, kind="branch"))
    for t in tags:
        labels.setdefault(t.commit_hash, []).append(SvgLabel(text=t.name, kind="tag"))
    return labels
```

- [ ] **Step 5: `_build_layer0` に `head_hash` を追加して HEAD フラグをセットする**

`_build_layer0` の関数定義を変更する。

変更前:
```python
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
```

変更後:
```python
def _build_layer0(
    tips: list[Commit],
    layer: GraphLayer,
    commit_to_node: dict[str, GraphNode],
    children_map: dict[str, list[str]],
    labels: dict[str, list[SvgLabel]],
    color_idx: list[int],
    head_hash: str | None,
) -> None:
    """Phase 2: Layer 0 を構築し commit_to_node を初期化する。"""
    for tip in tips:
        color = LANE_COLORS[color_idx[0] % len(LANE_COLORS)]
        color_idx[0] += 1
        branch = GraphBranch(color=color, refs=[lbl.text for lbl in labels.get(tip.hash, [])])
        line = GraphLine(branch=branch, color=color, is_main=True)
        if tip.hash == head_hash:
            line.is_head_branch = True
```

`build_graph` 内の `_build_layer0` 呼び出しを変更する。

変更前:
```python
    _build_layer0(tips, layer0, commit_to_node, children_map, labels, color_idx)
```

変更後:
```python
    _build_layer0(tips, layer0, commit_to_node, children_map, labels, color_idx, head_hash)
```

- [ ] **Step 6: テストがパスすることを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py -v
```

期待出力: 全テスト PASSED

- [ ] **Step 7: コミット**

```bash
git add backend/services/graph_builder.py tests/unit/test_graph_builder.py
git commit -m "feat: SvgLabel 型に移行し HEAD ブランチフラグを設定する"
```

---

## Task 5: `_resolve_node_type` と `_make_svg_node` の更新（graph_coords.py）

**Files:**
- Modify: `backend/services/graph_coords.py`
- Modify: `tests/unit/test_graph_coords.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/unit/test_graph_coords.py` の import 行を更新し、末尾にテストを追加する。

import 行に追加:
```python
from backend.services.graph_coords import _resolve_node_type
```

末尾に追加するテスト:
```python
def test_resolve_node_type_layer0の実ノードはtip():
    # --- Arrange ---
    branch = GraphBranch(color="#aaa")
    line = GraphLine(branch=branch, color="#aaa")
    layer = GraphLayer(index=0)
    node = GraphNode(commit=_c("a", 1), layer=layer, primary_line=line, dummy=False)

    # --- Act ---
    result = _resolve_node_type(node, layer, {})

    # --- Assert ---
    assert result == "tip"


def test_resolve_node_type_親なしコミットはroot():
    # --- Arrange ---
    branch = GraphBranch(color="#aaa")
    line = GraphLine(branch=branch, color="#aaa")
    layer = GraphLayer(index=1)
    node = GraphNode(commit=_c("a", 1), layer=layer, primary_line=line, dummy=False)

    # --- Act ---
    result = _resolve_node_type(node, layer, {})

    # --- Assert ---
    assert result == "root"


def test_resolve_node_type_親が2つ以上ならmerge():
    # --- Arrange ---
    branch = GraphBranch(color="#aaa")
    line = GraphLine(branch=branch, color="#aaa")
    layer = GraphLayer(index=1)
    node = GraphNode(commit=_c("m", 4), layer=layer, primary_line=line, dummy=False)
    parents = {"m" * 40: ["a" * 40, "b" * 40]}

    # --- Act ---
    result = _resolve_node_type(node, layer, parents)

    # --- Assert ---
    assert result == "merge"


def test_resolve_node_type_通常コミットはregular():
    # --- Arrange ---
    branch = GraphBranch(color="#aaa")
    line = GraphLine(branch=branch, color="#aaa")
    layer = GraphLayer(index=1)
    node = GraphNode(commit=_c("b", 2), layer=layer, primary_line=line, dummy=False)
    parents = {"b" * 40: ["a" * 40]}

    # --- Act ---
    result = _resolve_node_type(node, layer, parents)

    # --- Assert ---
    assert result == "regular"


def test_build_graph_TIPノードのnode_typeはtip():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [Branch(name="main", repo_id=_REPO_ID, tip_hash="b" * 40, is_remote=0)]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    tip_node = next(n for n in result.nodes if n.commit.hash == "b" * 40)
    assert tip_node.node_type == "tip"


def test_build_graph_ROOTノードのnode_typeはroot():
    # --- Arrange ---
    commits = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [Branch(name="main", repo_id=_REPO_ID, tip_hash="b" * 40, is_remote=0)]

    # --- Act ---
    result = build_graph(commits, parents, branches, [])

    # --- Assert ---
    root_node = next(n for n in result.nodes if n.commit.hash == "a" * 40)
    assert root_node.node_type == "root"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run task test tests/unit/test_graph_coords.py::test_resolve_node_type_layer0の実ノードはtip -v
```

期待出力: FAILED（ImportError または AttributeError）

- [ ] **Step 3: `graph_coords.py` に `_resolve_node_type` を追加し `_make_svg_node` を更新する**

`assign_coords` の後、`_make_svg_node` の前に `_resolve_node_type` を追加する:

```python
def _resolve_node_type(
    node: GraphNode,
    layer: GraphLayer,
    parents: dict[str, list[str]],
) -> NodeType:
    """ノード種別を判定する。"""
    if layer.index == 0 and not node.dummy:
        return "tip"
    parent_hashes = parents.get(node.commit.hash, [])
    if not parent_hashes:
        return "root"
    if len(parent_hashes) >= 2:
        return "merge"
    return "regular"
```

import に `NodeType` を追加する:

変更前:
```python
from backend.services.graph_models import (
    MARGIN_TOP,
    SPACING_X,
    SPACING_Y,
    GraphLayer,
    GraphNode,
    GraphResult,
    SvgEdge,
    SvgLabel,
    SvgNode,
)
```

変更後:
```python
from backend.services.graph_models import (
    MARGIN_TOP,
    SPACING_X,
    SPACING_Y,
    GraphLayer,
    GraphNode,
    GraphResult,
    NodeType,
    SvgEdge,
    SvgLabel,
    SvgNode,
)
```

`_make_svg_node` を更新して `node_type` をセットする:

変更前:
```python
def _make_svg_node(
    node: GraphNode,
    layer: GraphLayer,
    labels_by_hash: dict[str, list[SvgLabel]],
) -> SvgNode:
    """単一ノードの SvgNode を生成する。"""
    return SvgNode(
        cx=node.x * SPACING_X,
        cy=layer.y,
        color=node.primary_line.color,
        commit=node.commit,
        labels=labels_by_hash.get(node.commit.hash, []),
    )
```

変更後:
```python
def _make_svg_node(
    node: GraphNode,
    layer: GraphLayer,
    parents: dict[str, list[str]],
    labels_by_hash: dict[str, list[SvgLabel]],
) -> SvgNode:
    """単一ノードの SvgNode を生成する。"""
    return SvgNode(
        cx=node.x * SPACING_X,
        cy=layer.y,
        color=node.primary_line.color,
        commit=node.commit,
        labels=labels_by_hash.get(node.commit.hash, []),
        node_type=_resolve_node_type(node, layer, parents),
    )
```

`to_svg` 内の `_make_svg_node` 呼び出しに `parents` を追加する:

変更前:
```python
            svg_nodes.append(_make_svg_node(node, layer, labels_by_hash))
```

変更後:
```python
            svg_nodes.append(_make_svg_node(node, layer, parents, labels_by_hash))
```

- [ ] **Step 4: テストがパスすることを確認する**

```bash
uv run task test tests/unit/test_graph_coords.py tests/unit/test_graph_builder.py -v
```

期待出力: 全テスト PASSED

- [ ] **Step 5: コミット**

```bash
git add backend/services/graph_coords.py tests/unit/test_graph_coords.py
git commit -m "feat: _resolve_node_type を追加し SvgNode.node_type を設定する"
```

---

## Task 6: テンプレート更新（graph.html）

**Files:**
- Modify: `backend/templates/graph.html`

- [ ] **Step 1: `graph.html` を以下の内容に置き換える**

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
        {# エッジ: HEAD ブランチは太線 4pt、その他は 2pt #}
        {% for edge in edges %}
          <path
            d="{{ edge.d }}"
            stroke="{{ edge.color }}"
            stroke-width="{% if edge.is_main %}4{% else %}2{% endif %}"
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
            {# ノード種別: tip/root は中空大, merge は中空中, regular は塗りつぶし小 #}
            {% if node.node_type in ("tip", "root") %}
              <circle cx="{{ node.cx }}" cy="{{ node.cy }}" r="9"
                      fill="none" stroke="{{ node.color }}" stroke-width="2.5"/>
            {% elif node.node_type == "merge" %}
              <circle cx="{{ node.cx }}" cy="{{ node.cy }}" r="7"
                      fill="none" stroke="{{ node.color }}" stroke-width="2.5"/>
            {% else %}
              <circle cx="{{ node.cx }}" cy="{{ node.cy }}" r="5" fill="{{ node.color }}"/>
            {% endif %}

            {# バッジラベル: head=不透明, branch=半透明, tag=枠線のみ #}
            {% set badge_x = node.cx + 14 %}
            {% for label in node.labels %}
              {% set badge_w = (label.text | length) * 7 + 8 %}
              {% if label.kind == "head" %}
                <rect x="{{ badge_x }}" y="{{ node.cy - 8 }}"
                      width="{{ badge_w }}" height="16" rx="3"
                      fill="{{ node.color }}"/>
                <text x="{{ badge_x + badge_w / 2 }}" y="{{ node.cy + 4 }}"
                      font-size="9" fill="#fff" font-weight="bold"
                      font-family="monospace" text-anchor="middle"
                      pointer-events="none">{{ label.text }}</text>
              {% elif label.kind == "branch" %}
                <rect x="{{ badge_x }}" y="{{ node.cy - 8 }}"
                      width="{{ badge_w }}" height="16" rx="3"
                      fill="{{ node.color }}" opacity="0.65"/>
                <text x="{{ badge_x + badge_w / 2 }}" y="{{ node.cy + 4 }}"
                      font-size="9" fill="#fff"
                      font-family="monospace" text-anchor="middle"
                      pointer-events="none">{{ label.text }}</text>
              {% else %}
                <rect x="{{ badge_x }}" y="{{ node.cy - 8 }}"
                      width="{{ badge_w }}" height="16" rx="7"
                      fill="none" stroke="#888" stroke-width="1"/>
                <text x="{{ badge_x + badge_w / 2 }}" y="{{ node.cy + 4 }}"
                      font-size="8" fill="#888"
                      font-family="monospace" text-anchor="middle"
                      pointer-events="none">{{ label.text }}</text>
              {% endif %}
              {% set badge_x = badge_x + badge_w + 4 %}
            {% endfor %}
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

ブラウザで `http://localhost:8000/repos/<repo_id>/graph` を開き、以下を目視確認する:
- ブランチ先端ノードが中空の大きい円（r=9）で表示される
- 通常コミットが小さい塗りつぶし円（r=5）で表示される
- HEAD が属するブランチのラインが太線（4pt）で表示される
- ブランチ名・HEAD が角丸バッジで表示される（HEAD は不透明、ブランチ名は半透明）
- タグが枠線のみのピル形バッジで表示される

- [ ] **Step 3: 全ユニットテストがパスすることを確認する**

```bash
uv run task test -v
```

期待出力: 全テスト PASSED

- [ ] **Step 4: コミット**

```bash
git add backend/templates/graph.html
git commit -m "feat: ノード種別・メインライン強調・バッジラベルをグラフテンプレートに適用する"
```
