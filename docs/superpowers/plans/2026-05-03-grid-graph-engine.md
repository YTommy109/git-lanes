# グリッドグラフエンジン実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docs/graph-algorithm.md` のグリッド方式アルゴリズムを実装し、11 ケースのテストで動作を検証する。

**Architecture:** 既存の gitup エンジン（`graph_builder.py` 等）はそのまま残し、`grid_builder.py` / `grid_models.py` / `grid_coords.py` を新規追加する。`build_layout()` 関数（テスト用・中間結果を返す）と `build_grid()` 関数（ルーター用・`GraphResult` を返す）の 2 層構造とする。ルーターの import を 1 行変更して新エンジンに切り替える。

**Tech Stack:** Python 3.12, dataclasses, pytest, 既存の SQLModel モデル（Commit / Branch / Tag）

---

## ファイルマップ

| 操作 | パス | 用途 |
|------|------|------|
| 新規 | `backend/services/grid_models.py` | GridNode / GridEdge / GridLayout / GridResult 型定義 |
| 新規 | `backend/services/grid_builder.py` | レーン割り当て・ノード配置・エッジ生成・build_grid() |
| 新規 | `backend/services/grid_coords.py` | GridLayout → GraphResult（SVG 変換） |
| 新規 | `tests/unit/test_grid_builder.py` | 11 ケースの単体テスト |
| 変更 | `backend/services/graph_models.py` | SvgEdge に `dashed: bool = False` フィールドを追加 |
| 変更 | `backend/templates/graph.html` | dashed=True のエッジに stroke-dasharray を適用 |
| 変更 | `backend/routers/html.py` | import 先を grid_builder に切り替え |

---

## 座標・色の定数（全タスクで参照）

```
レーン N の cx = 20 + N × 30
行 M の cy = 72 + M × 30
```

ブランチ色（登場順）:
```
index 0: #4a9cf6  index 1: #f0883e  index 2: #3fb950  index 3: #e5534b
index 4: #a371f7  index 5: #f778ba  index 6: #39c5cf  index 7: #d4a72c
```

ケースごとの期待値（SVG から逆算した lane / row）:

| ケース | コミット | lane | row | kind |
|--------|----------|------|-----|------|
| 1 | a | 1 | 0 | commit |
| 2 | b(新) | 1 | 0 | commit |
| 2 | a(旧) | 1 | 1 | commit |
| 3 | a | 1 | 0 | commit |
| 4 | a(main) | 1 | 0 | commit |
| 4 | b(develop) | 4 | 0 | commit |
| 4 | c(共通親) | 1 | 1 | commit |
| 5 | a2 | 1 | 0 | commit |
| 5 | dummy(develop) | 4 | 0 | dummy |
| 5 | a1 | 1 | 1 | commit |
| 5 | b1 | 4 | 1 | commit |
| 5 | a0 | 1 | 2 | commit |
| 6 | a2 | 1 | 0 | commit |
| 6 | dummy(develop) | 4 | 0 | dummy |
| 6 | a1 | 1 | 1 | commit |
| 6 | joint(dev) | 4 | 1 | joint |
| 6 | a0 | 1 | 2 | commit |
| 7 | dummy(main) | 1 | 0 | dummy |
| 7 | b1 | 4 | 0 | commit |
| 7 | a0 | 1 | 1 | commit |
| 8 | a1 | 1 | 0 | commit |
| 8 | b1 | 2 | 1 | commit |
| 8 | a0 | 1 | 2 | commit |
| 9 | a1 | 1 | 0 | commit |
| 9 | b3 | 2 | 1 | commit |
| 9 | b2 | 2 | 2 | commit |
| 9 | b1 | 2 | 3 | commit |
| 9 | a0 | 1 | 4 | commit |
| 10 | a1 | 1 | 0 | commit |
| 10 | dummy(feat) | 4 | 0 | dummy |
| 10 | b1 | 2 | 1 | commit |
| 10 | c1 | 4 | 1 | commit |
| 10 | a0 | 1 | 2 | commit |
| 11 | a2 | 1 | 0 | commit |
| 11 | a1 | 1 | 1 | commit |
| 11 | c1 | 3 | 1 | commit |
| 11 | b1 | 2 | 2 | commit |
| 11 | joint(c1) | 3 | 2 | joint |
| 11 | a0 | 1 | 3 | commit |

---

## Task 1: SvgEdge に dashed フィールドを追加する

**Files:**
- Modify: `backend/services/graph_models.py`
- Modify: `backend/templates/graph.html`

- [ ] **Step 1: graph_models.py に dashed フィールドを追加する**

`backend/services/graph_models.py` の `SvgEdge` クラスを以下に変更する（既存フィールドの後に追加）:

```python
@dataclass
class SvgEdge:
    """SVG テンプレートへ渡すエッジ情報。"""

    d: str
    color: str
    is_main: bool = False
    dashed: bool = False
```

- [ ] **Step 2: graph.html でダッシュを適用する**

`backend/templates/graph.html` を開き、`<path>` タグでエッジを描画している箇所を確認する。`dashed` が True の場合に `stroke-dasharray="4,3"` を適用するよう修正する。

例（既存の path タグの形式に合わせること）:
```html
<path d="{{ edge.d }}"
      stroke="{{ edge.color }}"
      stroke-width="{{ '2.5' if edge.is_main else '1.5' }}"
      {% if edge.dashed %}stroke-dasharray="4,3"{% endif %}
      fill="none"/>
```

- [ ] **Step 3: 既存テストが通ることを確認する**

```bash
uv run task test
```

Expected: 全テスト PASS（`dashed` のデフォルト値が `False` のため既存動作に影響なし）

- [ ] **Step 4: コミットする**

```bash
git add backend/services/graph_models.py backend/templates/graph.html
git commit -m "feat: SvgEdge に dashed フィールドを追加する"
```

---

## Task 2: データモデルとテストヘルパーを作成する

**Files:**
- Create: `backend/services/grid_models.py`
- Create: `tests/unit/test_grid_builder.py`

- [ ] **Step 1: grid_models.py を作成する**

```python
# backend/services/grid_models.py
"""グリッドグラフエンジンのデータモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal["commit", "dummy", "joint"]

GRID_COLORS: list[str] = [
    "#4a9cf6",
    "#f0883e",
    "#3fb950",
    "#e5534b",
    "#a371f7",
    "#f778ba",
    "#39c5cf",
    "#d4a72c",
]

GRID_SPACING: int = 30
GRID_ORIGIN_X: int = 20   # レーン N の cx = GRID_ORIGIN_X + N * GRID_SPACING
GRID_ORIGIN_Y: int = 72   # 行 M の cy = GRID_ORIGIN_Y + M * GRID_SPACING


@dataclass
class GridNode:
    """グリッド座標上のノード。joint は hash=None。"""

    hash: str | None
    lane: int
    row: int
    kind: NodeKind
    color: str


@dataclass
class GridEdge:
    """グリッド座標上のエッジ。"""

    from_lane: int
    from_row: int
    to_lane: int
    to_row: int
    color: str
    dashed: bool


@dataclass
class GridBranchLabel:
    """ブランチ名ラベル情報。"""

    lane: int
    names: list[str]
    color: str


@dataclass
class GridLayout:
    """build_layout() の返り値（テスト用中間表現）。"""

    nodes: list[GridNode] = field(default_factory=list)
    edges: list[GridEdge] = field(default_factory=list)
    branch_labels: list[GridBranchLabel] = field(default_factory=list)
```

- [ ] **Step 2: テストファイルのヘルパー関数を作成する**

```python
# tests/unit/test_grid_builder.py
"""grid_builder の単体テスト。11 ケース対応。"""

from __future__ import annotations

import pytest
from backend.models import Branch, Commit, Tag
from backend.services.grid_builder import build_layout
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
    assert node is not None, f"ノード '{h}' が見つからない。nodes={[(n.hash, n.lane, n.row) for n in layout.nodes]}"
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
            e for e in layout.edges
            if e.from_lane == from_node.lane and e.from_row == from_node.row
            and e.to_lane == to_node.lane and e.to_row == to_node.row
        ),
        None,
    )
    assert edge is not None, (
        f"エッジ '{from_h}'({from_node.lane},{from_node.row})"
        f"→'{to_h}'({to_node.lane},{to_node.row}) が見つからない。"
        f"edges={[(e.from_lane,e.from_row,e.to_lane,e.to_row) for e in layout.edges]}"
    )
    assert edge.dashed == dashed, f"エッジ '{from_h}'→'{to_h}' dashed: 実際={edge.dashed} 期待={dashed}"


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
            e for e in layout.edges
            if e.from_lane == from_lane and e.from_row == from_row
            and e.to_lane == to_lane and e.to_row == to_row
        ),
        None,
    )
    assert edge is not None, (
        f"エッジ ({from_lane},{from_row})→({to_lane},{to_row}) が見つからない。"
        f"edges={[(e.from_lane,e.from_row,e.to_lane,e.to_row) for e in layout.edges]}"
    )
    assert edge.dashed == dashed, (
        f"エッジ ({from_lane},{from_row})→({to_lane},{to_row}) dashed: 実際={edge.dashed} 期待={dashed}"
    )
```

- [ ] **Step 3: grid_builder.py のスタブを作成する（テスト実行のため）**

```python
# backend/services/grid_builder.py
"""グリッドグラフエンジン。"""

from __future__ import annotations

from backend.models import Branch, Commit, Tag
from backend.services.graph_models import GraphResult
from backend.services.grid_models import GridLayout


def build_layout(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GridLayout:
    """グリッドレイアウトを計算する（テスト用）。"""
    return GridLayout()


def build_grid(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GraphResult:
    """グリッドエンジンでグラフを構築して GraphResult を返す。"""
    from backend.services.grid_coords import to_svg

    layout = build_layout(commits, parents, branches, tags, head_hash)
    return to_svg(layout)
```

- [ ] **Step 4: grid_coords.py のスタブを作成する**

```python
# backend/services/grid_coords.py
"""GridLayout → GraphResult（SVG 変換）。"""

from __future__ import annotations

from backend.services.graph_models import GraphResult, SvgBranchHeader, SvgEdge, SvgNode
from backend.services.grid_models import GridLayout


def to_svg(layout: GridLayout) -> GraphResult:
    """GridLayout を GraphResult に変換する。"""
    return GraphResult(
        nodes=[],
        edges=[],
        branch_headers=[],
        canvas_width=100.0,
        canvas_height=100.0,
    )
```

- [ ] **Step 5: テストファイルが import できることを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py --collect-only
```

Expected: `no tests ran` （テスト関数がまだないため）

- [ ] **Step 6: コミットする**

```bash
git add backend/services/grid_models.py backend/services/grid_builder.py backend/services/grid_coords.py tests/unit/test_grid_builder.py
git commit -m "feat: グリッドグラフエンジンの骨格を追加する"
```

---

## Task 3: ケース 1 - コミット 1 つ（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`
- Modify: `backend/services/grid_builder.py`

- [ ] **Step 1: テストを追加する**

`tests/unit/test_grid_builder.py` の末尾に追加:

```python
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
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース1_コミット1つ -v
```

Expected: FAIL（`build_layout` が空の `GridLayout` を返すため）

- [ ] **Step 3: ケース 1 を通す最小実装を `grid_builder.py` に書く**

`build_layout` を以下で置き換える:

```python
def build_layout(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GridLayout:
    """グリッドレイアウトを計算する（テスト用）。"""
    from backend.services.grid_models import (
        GRID_COLORS,
        GridBranchLabel,
        GridEdge,
        GridNode,
        GridLayout,
    )

    # ブランチ先端マップ: tip_hash → [branch_name]
    tip_to_names: dict[str, list[str]] = {}
    for b in branches:
        tip_to_names.setdefault(b.tip_hash, []).append(b.name)

    # ブランチレーン番号を事前割り当て: branches リスト順に 1, 4, 7, ...
    branch_lane: dict[str, int] = {}  # branch_name → lane_num
    lane_num = 1
    for b in branches:
        if b.name not in branch_lane:
            branch_lane[b.name] = lane_num
            lane_num += 3

    # tip_hash → lane_num（named branch のみ）
    tip_lane: dict[str, int] = {}
    for b in branches:
        tip_lane[b.tip_hash] = branch_lane[b.name]

    # ブランチ色（登場順）
    color_map: dict[str, str] = {}
    color_idx = 0
    for b in branches:
        if b.name not in color_map:
            color_map[b.name] = GRID_COLORS[color_idx % len(GRID_COLORS)]
            color_idx += 1

    # tip_hash → color
    tip_color: dict[str, str] = {}
    for b in branches:
        tip_color[b.tip_hash] = color_map[b.name]

    layout = GridLayout()

    # コミットを committed_at 降順でグループ化（同じ at = 同じ row）
    from itertools import groupby
    sorted_commits = sorted(commits, key=lambda c: -c.committed_at)
    row = 0
    placed: dict[str, GridNode] = {}  # hash → GridNode

    # active_lanes: list of (lane_num, bottom_hash, color)
    active_lanes: list[tuple[int, str, str]] = []
    used_branch_lanes: set[int] = set()

    for _, group in groupby(sorted_commits, key=lambda c: c.committed_at):
        group_commits = list(group)
        for commit in group_commits:
            h = commit.hash
            commit_parents = parents.get(h, [])

            # このコミットを受け入れる active_lane を探す
            matched_lane: int | None = None
            matched_color: str | None = None
            new_active: list[tuple[int, str, str]] = []

            for ln, bottom_h, color in active_lanes:
                bottom_parents = parents.get(bottom_h, [])
                if h in bottom_parents and matched_lane is None:
                    matched_lane = ln
                    matched_color = color
                    # このレーンの bottom を h に更新
                    new_active.append((ln, h, color))
                else:
                    new_active.append((ln, bottom_h, color))
            active_lanes = new_active

            if matched_lane is None:
                # 新しいレーンを作る
                if h in tip_lane:
                    # named branch tip → 事前割り当てレーン
                    matched_lane = tip_lane[h]
                    matched_color = tip_color.get(h, GRID_COLORS[0])
                    used_branch_lanes.add(matched_lane)
                else:
                    # 削除済み/unnamed → 中間レーン（2, 3, 5, 6, ...）
                    matched_lane = _next_middle_lane(used_branch_lanes)
                    matched_color = GRID_COLORS[color_idx % len(GRID_COLORS)]
                    color_idx += 1
                active_lanes.append((matched_lane, h, matched_color))

            node = GridNode(
                hash=h,
                lane=matched_lane,
                row=row,
                kind="commit",
                color=matched_color or GRID_COLORS[0],
            )
            placed[h] = node
            layout.nodes.append(node)

        row += 1

    return layout


def _next_middle_lane(used_branch_lanes: set[int]) -> int:
    """使用済みブランチレーン間の未使用中間レーン番号を返す。"""
    candidate = 2
    while True:
        if candidate not in used_branch_lanes:
            # ブランチレーンでなければ中間レーン
            is_branch_lane = (candidate - 1) % 3 == 0 and candidate >= 1
            if not is_branch_lane:
                return candidate
        candidate += 1
```

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース1_コミット1つ -v
```

Expected: PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース1（コミット1つ）を追加し実装する"
```

---

## Task 4: ケース 2 - 直線接続（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`
- Modify: `backend/services/grid_builder.py`

- [ ] **Step 1: テストを追加する**

```python
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
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース2_直線接続 -v
```

Expected: FAIL（エッジ生成がまだ未実装）

- [ ] **Step 3: エッジ生成を `build_layout` に追加する**

`build_layout` のノード配置ループの後（`return layout` の前）に以下を追加する:

```python
    # エッジ生成: 各コミットから親へのエッジ
    for node in layout.nodes:
        if node.kind != "commit":
            continue
        commit_parents = parents.get(node.hash or "", [])
        for p_hash in commit_parents:
            if p_hash not in placed:
                continue
            p_node = placed[p_hash]
            row_diff = abs(p_node.row - node.row)
            if node.lane == p_node.lane:
                # 同一レーン: 縦エッジ（複数行またぎも可）
                layout.edges.append(GridEdge(
                    from_lane=node.lane, from_row=node.row,
                    to_lane=p_node.lane, to_row=p_node.row,
                    color=node.color, dashed=False,
                ))
            elif row_diff == 1:
                # 異なるレーン・1行差: 斜めエッジ
                layout.edges.append(GridEdge(
                    from_lane=node.lane, from_row=node.row,
                    to_lane=p_node.lane, to_row=p_node.row,
                    color=node.color, dashed=False,
                ))
            else:
                # 異なるレーン・複数行差: ジョイントノードで中継
                _add_joint_edges(layout, node, p_node)

    return layout
```

同じファイルに以下のヘルパーを追加する:

```python
def _add_joint_edges(
    layout: "GridLayout",
    from_node: "GridNode",
    to_node: "GridNode",
) -> None:
    """複数行をまたぐ斜めエッジをジョイントノードで 1 行ずつ分割する。"""
    from backend.services.grid_models import GridEdge, GridNode

    cur_lane = from_node.lane
    cur_row = from_node.row
    target_lane = to_node.lane
    target_row = to_node.row

    while cur_row + 1 < target_row:
        next_row = cur_row + 1
        # 目標のレーンに向かって 1 行ずつ移動（最終行の 1 つ前まで垂直）
        joint = GridNode(
            hash=None,
            lane=cur_lane,
            row=next_row,
            kind="joint",
            color=from_node.color,
        )
        layout.nodes.append(joint)
        layout.edges.append(GridEdge(
            from_lane=cur_lane, from_row=cur_row,
            to_lane=cur_lane, to_row=next_row,
            color=from_node.color, dashed=True,
        ))
        cur_row = next_row

    # 最後の 1 行: 斜め
    layout.edges.append(GridEdge(
        from_lane=cur_lane, from_row=cur_row,
        to_lane=target_lane, to_row=target_row,
        color=from_node.color, dashed=True,
    ))
```

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース2_直線接続 -v
```

Expected: PASS

- [ ] **Step 5: ケース 1 も壊れていないことを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 2 tests PASS

- [ ] **Step 6: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース2（直線接続）を追加し実装する"
```

---

## Task 5: ケース 3 - 同じコミットを指す 2 ブランチ（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

- [ ] **Step 1: テストを追加する**

```python
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
    # develop ラベルも lane 1 に存在する
    lane1_labels = next((lb for lb in layout.branch_labels if lb.lane == 1), None)
    assert lane1_labels is not None
    assert "develop" in lane1_labels.names
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース3_同じコミットを指す2ブランチ -v
```

Expected: FAIL（`branch_labels` が未実装）

- [ ] **Step 3: branch_labels の生成を `build_layout` に追加する**

`build_layout` の `return layout` の直前に以下を追加する:

```python
    # branch_labels: レーンごとのブランチ名ラベルを生成
    # 同じ tip_hash を持つブランチは同じレーンにまとめる
    lane_to_names: dict[int, list[str]] = {}
    lane_to_color: dict[int, str] = {}
    for b in branches:
        tip_h = b.tip_hash
        if tip_h in placed:
            node = placed[tip_h]
            target_lane = node.lane
        elif tip_h in tip_lane:
            target_lane = tip_lane[tip_h]
        else:
            continue
        lane_to_names.setdefault(target_lane, []).append(b.name)
        lane_to_color[target_lane] = color_map.get(b.name, GRID_COLORS[0])

    for ln, names in lane_to_names.items():
        layout.branch_labels.append(GridBranchLabel(
            lane=ln,
            names=names,
            color=lane_to_color[ln],
        ))
```

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース3（同じコミットを指す2ブランチ）を追加し実装する"
```

---

## Task 6: ケース 4 - 2 ブランチが同じ親を持つ（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

注意: a と b を同じ at=2 にすることで row=0 を共有させる。

- [ ] **Step 1: テストを追加する**

```python
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
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース4_2ブランチが同じ親を持つ -v
```

Expected: FAIL

- [ ] **Step 3: 同一 at のコミットが同じ row を共有するように `build_layout` を修正する**

`build_layout` の `sorted_commits` ループを確認する。`groupby(sorted_commits, key=lambda c: c.committed_at)` が正しく動いていれば同一 at は同一 row になる。

もし row が増分されているなら、groupby の外の `row += 1` が内側に移動しているか確認する。正しい構造:

```python
    row = 0
    for _, group in groupby(sorted_commits, key=lambda c: c.committed_at):
        group_commits = list(group)
        for commit in group_commits:
            # ... コミットを row に配置 ...
            pass
        row += 1  # ← group（同一 at）が終わったら row を進める
```

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース4（2ブランチが同じ親を持つ）を追加し実装する"
```

---

## Task 7: ケース 5 - develop が main の途中から分岐（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`
- Modify: `backend/services/grid_builder.py`

ダミーノードが必要なケース: b1 が row=1 に配置されるため、develop レーン（lane=4）の row=0 にダミーが必要。

- [ ] **Step 1: テストを追加する**

```python
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
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース5_developがmainの途中から分岐 -v
```

Expected: FAIL（ダミーノード未実装）

- [ ] **Step 3: ダミーノード生成を `build_layout` に追加する**

エッジ生成の前（ノード配置ループの後）に以下を追加する:

```python
    # ダミーノード生成: named branch の tip が row=0 にない場合
    for b in branches:
        tip_h = b.tip_hash
        if tip_h not in placed:
            continue
        tip_node = placed[tip_h]
        if tip_node.row == 0:
            continue  # row=0 にあればダミー不要
        # row=0 にダミーを追加
        dummy = GridNode(
            hash=None,
            lane=tip_node.lane,
            row=0,
            kind="dummy",
            color=tip_node.color,
        )
        layout.nodes.append(dummy)
        # ダミー → tip_node へのエッジ（縦、破線）
        layout.edges.append(GridEdge(
            from_lane=tip_node.lane, from_row=0,
            to_lane=tip_node.lane, to_row=tip_node.row,
            color=tip_node.color, dashed=True,
        ))
```

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース5（developがmainの途中から分岐）を追加し実装する"
```

---

## Task 8: ケース 6 - develop が古いコミットを指す（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

ジョイントノードが必要: develop tip（a0）が row=2 にあり、ダミーから a0 まで 2 行の対角線 → (4,0)→(4,1) 縦破線 + (4,1)→(1,2) 斜め破線。

- [ ] **Step 1: テストを追加する**

```python
def test_ケース6_developが古いコミットを指す():
    # --- Arrange ---
    # develop は a0 を直接指している（別の特定コミットではなく main の旧コミット）
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
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース6_developが古いコミットを指す -v
```

Expected: FAIL（ダミー→コミット間のジョイントノード生成が未実装）

- [ ] **Step 3: ダミーからの多行接続でジョイントノードを生成するよう修正する**

ダミーノード生成ブロックの `layout.edges.append` を以下のロジックに置き換える:

```python
        # ダミー → tip_node まで接続
        # tip_node が同じレーンにある場合は縦エッジ（ジョイント不要）
        # tip_node が別レーンにある場合は _add_dummy_to_commit_edges で処理
        # ※ここでは dummy と tip_node が同一レーンのケース（ケース 5, 7）
        layout.edges.append(GridEdge(
            from_lane=tip_node.lane, from_row=0,
            to_lane=tip_node.lane, to_row=tip_node.row,
            color=tip_node.color, dashed=True,
        ))
```

次に、ケース 6 のように **develop のダミーが別レーンにある a0 を指す** 場合を処理する。

develop の `tip_hash=a0` で `a0` は lane=1 にある（main が先に取得）。develop は pre-assigned lane=4 でダミーを置く。

ダミーの接続先は a0（lane=1, row=2）。lane=4 から lane=1 への接続が 2 行またぎ → ジョイントノード必要。

ダミー生成ブロックを以下に置き換える:

```python
    # ダミーノード生成: named branch の tip が row=0 にない場合
    for b in branches:
        tip_h = b.tip_hash
        if tip_h not in placed:
            continue
        tip_node = placed[tip_h]
        if tip_node.row == 0:
            continue

        dummy_lane = tip_lane.get(b.tip_hash, tip_node.lane)
        dummy_color = color_map.get(b.name, GRID_COLORS[0])
        dummy = GridNode(hash=None, lane=dummy_lane, row=0, kind="dummy", color=dummy_color)
        layout.nodes.append(dummy)

        # ダミー → tip_node の接続
        if dummy_lane == tip_node.lane:
            # 同一レーン: 縦破線（1本）
            layout.edges.append(GridEdge(
                from_lane=dummy_lane, from_row=0,
                to_lane=tip_node.lane, to_row=tip_node.row,
                color=dummy_color, dashed=True,
            ))
        else:
            # 別レーン: ジョイントノードで 1 行ずつ分割
            cur_lane = dummy_lane
            cur_row = 0
            for mid_row in range(1, tip_node.row):
                joint = GridNode(hash=None, lane=cur_lane, row=mid_row, kind="joint", color=dummy_color)
                layout.nodes.append(joint)
                layout.edges.append(GridEdge(
                    from_lane=cur_lane, from_row=cur_row,
                    to_lane=cur_lane, to_row=mid_row,
                    color=dummy_color, dashed=True,
                ))
                cur_row = mid_row
            # 最後の 1 行は斜め
            layout.edges.append(GridEdge(
                from_lane=cur_lane, from_row=cur_row,
                to_lane=tip_node.lane, to_row=tip_node.row,
                color=dummy_color, dashed=True,
            ))
```

注意: `dummy_lane` は develop の pre-assigned lane（4）、`tip_node.lane` は a0 が実際に配置されたレーン（1）の可能性がある。`tip_lane` は tip_hash → lane_num のマップなので、同じ tip_hash でも a0 の実配置レーン（1）を使う必要がある。以下で tip_node.lane（実配置）を参照すること。

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース6（developが古いコミットを指す）を追加し実装する"
```

---

## Task 9: ケース 7 - develop の方が main より新しい（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

main の tip（a0）が row=1 に配置されるため、main レーン（lane=1）の row=0 にダミーが必要。

- [ ] **Step 1: テストを追加する**

```python
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
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース7_developがmainより新しい -v
```

Expected: FAIL

- [ ] **Step 3: ダミー生成ロジックが named branch の全 tip をカバーするか確認する**

現在のダミー生成ブロックは `branches` リストをループしている。ケース 7 では main の tip=a0 が row=1 にあるため、main ブランチのループでダミーが生成されるはず。

デバッグ: テスト失敗メッセージを読み、何が足りないかを確認してから修正する。

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 7 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース7（developがmainより新しい）を追加し実装する"
```

---

## Task 10: ケース 8 - マージ済み・ブランチ名削除済み（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`
- Modify: `backend/services/grid_builder.py`

マージコミット（parents が 2 つ）: a1.parents = ["a0", "b1"]（a0 = main の第 1 親、b1 = 削除済み develop の第 2 親）。b1 は削除済みブランチのため lane=2（中間レーン）に入る。

- [ ] **Step 1: テストを追加する**

```python
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
    # a1→b1 斜めエッジ（develop色）
    assert_edge(layout, "a1", "b1", dashed=False)
    # b1→a0 斜めエッジ（develop色）
    assert_edge(layout, "b1", "a0", dashed=False)
    # ダミーなし
    assert len([n for n in layout.nodes if n.kind == "dummy"]) == 0
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース8_マージ済みブランチ名削除済み -v
```

Expected: FAIL（b1 が lane=2 に入らない可能性が高い）

- [ ] **Step 3: active_lanes を「期待するハッシュ」付きに変更し、マージ第 2 親を中間レーンに振り分ける**

**根本問題**: 現行の `active_lanes: list[tuple[lane, bottom_hash, color]]` は `bottom_hash` の全 parents を照合するため、マージコミットの第 1 親と第 2 親が区別できない（どちらも同じ bottom の parents リストに存在する）。

**修正方針**: `active_lanes` に `expected_hash` を追加し、レーンが「次に受け入れるハッシュ」を明示する。

`active_lanes` の型を `list[tuple[int, str, str, str]]` = `(lane_num, bottom_hash, expected_hash, color)` に変更する。

`build_layout` の全体を以下の構造に置き換える:

```python
    # active_lanes: (lane_num, bottom_hash, expected_hash, color)
    # expected_hash = このレーンが次に受け入れるコミットのハッシュ
    active_lanes: list[tuple[int, str, str, str]] = []
    used_lane_nums: set[int] = set()

    row = 0
    placed: dict[str, GridNode] = {}

    for _, group in groupby(sorted_commits, key=lambda c: c.committed_at):
        group_commits = list(group)
        for commit in group_commits:
            h = commit.hash
            commit_parents = parents.get(h, [])

            # expected_hash で照合（左から順に）
            matched_idx: int | None = None
            for i, (ln, bottom_h, expected_h, color) in enumerate(active_lanes):
                if h == expected_h and matched_idx is None:
                    matched_idx = i

            matched_lane: int | None = None
            matched_color: str | None = None
            new_active: list[tuple[int, str, str, str]] = []

            for i, (ln, bottom_h, expected_h, color) in enumerate(active_lanes):
                if i == matched_idx:
                    matched_lane = ln
                    matched_color = color
                    # レーンの expected を第 1 親に更新
                    p1 = commit_parents[0] if commit_parents else None
                    if p1:
                        new_active.append((ln, h, p1, color))
                    # 第 1 親がなければ（root）このレーンは終了
                else:
                    new_active.append((ln, bottom_h, expected_h, color))
            active_lanes = new_active

            if matched_lane is None:
                # 新しいレーンを作る
                if h in tip_lane:
                    matched_lane = tip_lane[h]
                    matched_color = tip_color.get(h, GRID_COLORS[0])
                else:
                    matched_lane = _next_available_lane(used_lane_nums)
                    matched_color = GRID_COLORS[color_idx % len(GRID_COLORS)]
                    color_idx += 1
                used_lane_nums.add(matched_lane)
                p1 = commit_parents[0] if commit_parents else None
                if p1:
                    active_lanes.append((matched_lane, h, p1, matched_color))

            node = GridNode(
                hash=h, lane=matched_lane, row=row,
                kind="commit", color=matched_color or GRID_COLORS[0],
            )
            placed[h] = node
            layout.nodes.append(node)

            # マージコミットの第 2 親以降: 新しいレーンを予約
            for p2_hash in commit_parents[1:]:
                if p2_hash in placed:
                    continue  # 既に配置済みなら不要
                p2_lane = _next_available_lane(used_lane_nums)
                p2_color = GRID_COLORS[color_idx % len(GRID_COLORS)]
                color_idx += 1
                used_lane_nums.add(p2_lane)
                active_lanes.append((p2_lane, h, p2_hash, p2_color))

        row += 1
```

`_next_middle_lane` を `_next_available_lane` に置き換える:

```python
def _next_available_lane(used: set[int]) -> int:
    """使用済みでない最小のレーン番号を返す。
    ブランチレーン（1,4,7,...）は tip_lane で事前割り当て済みのため、
    ここでは中間レーン（2,3,5,6,...）も含め単純に最小空き番号を返す。
    """
    candidate = 1
    while candidate in used:
        candidate += 1
    return candidate
```

注意: `tip_lane` の事前割り当て（1, 4, 7, ...）を `used_lane_nums` に初期投入してから処理を始めることで、中間レーンが自然に 2, 3, 5, 6, ... に割り当てられる:

```python
    # 事前割り当て済みのブランチレーンを used に追加
    used_lane_nums: set[int] = set(tip_lane.values())
```

この変更により、`_next_available_lane` が中間レーン（2, 3, ...）のみを返すようになる。

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 8 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース8（マージ済みブランチ名削除済み）を追加し実装する"
```

---

## Task 11: ケース 9 - マージ済み削除ブランチ（コミット複数）（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

削除済み develop に 3 コミット（b3→b2→b1→a0）。中間レーン（lane=2）に縦に並ぶ。

- [ ] **Step 1: テストを追加する**

```python
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
    parents = _p(commits, {
        "a1": ["a0", "b3"], "b3": ["b2"], "b2": ["b1"], "b1": ["a0"],
    })

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
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース9_マージ済み削除ブランチ複数コミット -v
```

Expected: FAIL

- [ ] **Step 3: テスト失敗内容を確認し修正する**

b3 が lane=2 に入らない場合: マージコミット a1 の第 2 親用レーン割り当てロジックを確認する。

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 9 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース9（マージ済み削除ブランチ複数コミット）を追加し実装する"
```

---

## Task 12: ケース 10 - 削除ブランチ + アクティブブランチ混在（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

feat/something01（名前あり、lane=4）と削除済み develop（lane=2）が混在。feat tip=c1 が row=1 のためダミー必要。

- [ ] **Step 1: テストを追加する**

```python
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
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース10_削除ブランチとアクティブブランチ混在 -v
```

Expected: FAIL

- [ ] **Step 3: テスト失敗内容を確認し修正する**

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 10 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース10（削除ブランチとアクティブブランチ混在）を追加し実装する"
```

---

## Task 13: ケース 11 - 2 ブランチをマージ後にどちらも削除（TDD）

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

削除済みブランチが 2 つ（develop: lane=2, feat: lane=3）。c1→a0 のジョイントノードが lane=3, row=2 に必要。

- [ ] **Step 1: テストを追加する**

```python
def test_ケース11_2ブランチをマージ後にどちらも削除():
    # --- Arrange ---
    # a1 と c1 は同じ at=3 → row 1 を共有
    commits = [
        _c("a2", parents=["a1", "c1"], at=4),
        _c("a1", parents=["a0", "b1"], at=3),
        _c("c1", parents=["a0"], at=3),
        _c("b1", parents=["a0"], at=2),
        _c("a0", parents=[], at=1),
    ]
    branches = [_b("main", "a2")]  # develop, feat はどちらも削除済み
    parents = _p(commits, {
        "a2": ["a1", "c1"],
        "a1": ["a0", "b1"],
        "c1": ["a0"],
        "b1": ["a0"],
    })

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    assert_node(layout, "a2", lane=1, row=0, kind="commit")
    assert_node(layout, "a1", lane=1, row=1, kind="commit")
    assert_node(layout, "c1", lane=3, row=1, kind="commit")
    assert_node(layout, "b1", lane=2, row=2, kind="commit")
    assert_node(layout, "a0", lane=1, row=3, kind="commit")
    # c1→a0 のジョイントノードが lane=3, row=2
    c1_joints = [n for n in layout.nodes if n.kind == "joint" and n.lane == 3]
    assert len(c1_joints) == 1
    assert c1_joints[0].row == 2
    # エッジ
    assert_edge(layout, "a2", "a1", dashed=False)
    assert_edge(layout, "a2", "c1", dashed=False)
    assert_edge(layout, "a1", "b1", dashed=False)
    assert_edge(layout, "a1", "a0", dashed=False)
    assert_edge(layout, "b1", "a0", dashed=False)
    # c1(3,1)→joint(3,2) 縦
    assert_edge_coords(layout, 3, 1, 3, 2, dashed=False)
    # joint(3,2)→a0(1,3) 斜め
    assert_edge_coords(layout, 3, 2, 1, 3, dashed=False)
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース11_2ブランチをマージ後にどちらも削除 -v
```

Expected: FAIL

- [ ] **Step 3: テスト失敗内容を確認し修正する**

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 11 tests PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/unit/test_grid_builder.py backend/services/grid_builder.py
git commit -m "test: ケース11（2ブランチをマージ後にどちらも削除）を追加し実装する"
```

---

## Task 14: grid_coords.py を実装する（SVG 変換）

**Files:**
- Modify: `backend/services/grid_coords.py`

`GridLayout` → `GraphResult`（`SvgNode` / `SvgEdge` / `SvgBranchHeader`）の変換を実装する。

- [ ] **Step 1: to_svg() を実装する**

```python
# backend/services/grid_coords.py
"""GridLayout → GraphResult（SVG 変換）。"""

from __future__ import annotations

from backend.models import Commit
from backend.services.graph_models import (
    GraphResult,
    SvgBranchHeader,
    SvgEdge,
    SvgLabel,
    SvgNode,
)
from backend.services.grid_models import (
    GRID_ORIGIN_X,
    GRID_ORIGIN_Y,
    GRID_SPACING,
    GridLayout,
    GridNode,
)


def _cx(lane: int) -> float:
    return float(GRID_ORIGIN_X + lane * GRID_SPACING)


def _cy(row: int) -> float:
    return float(GRID_ORIGIN_Y + row * GRID_SPACING)


def to_svg(layout: GridLayout) -> GraphResult:
    """GridLayout を GraphResult に変換する。"""
    # ノード変換（commit のみ描画; dummy は小円; joint は不可視）
    svg_nodes: list[SvgNode] = []
    # hash → Commit のマップ（SvgNode.commit に必要）
    # grid_builder からは Commit オブジェクトを持っていないため、ダミーの Commit を生成する
    # 実際の router 経由では commits リストが渡されるので _enrich で上書きする
    for node in layout.nodes:
        if node.kind == "joint":
            continue  # joint は SVG に描画しない
        if node.hash is None:
            continue  # dummy で hash なしは skip（別途処理）

        svg_nodes.append(SvgNode(
            cx=_cx(node.lane),
            cy=_cy(node.row),
            color=node.color,
            commit=_dummy_commit(node.hash),
            labels=[],
            node_type="regular",
        ))

    # エッジ変換
    svg_edges: list[SvgEdge] = []
    for edge in layout.edges:
        x1 = _cx(edge.from_lane)
        y1 = _cy(edge.from_row)
        x2 = _cx(edge.to_lane)
        y2 = _cy(edge.to_row)
        svg_edges.append(SvgEdge(
            d=f"M {x1} {y1} L {x2} {y2}",
            color=edge.color,
            is_main=False,
            dashed=edge.dashed,
        ))

    # ブランチヘッダー変換
    svg_headers: list[SvgBranchHeader] = []
    label_y = GRID_ORIGIN_Y - GRID_SPACING  # ブランチ名ラベルの y（コミット行の上）
    for label in layout.branch_labels:
        svg_headers.append(SvgBranchHeader(
            cx=_cx(label.lane),
            cy=float(label_y),
            labels=[SvgLabel(text=n, kind="branch") for n in label.names],
            color=label.color,
            display_text=", ".join(label.names),
        ))

    # キャンバスサイズ
    all_cx = [_cx(n.lane) for n in layout.nodes] or [100.0]
    all_cy = [_cy(n.row) for n in layout.nodes] or [100.0]
    canvas_width = max(all_cx) + 60.0
    canvas_height = max(all_cy) + 40.0

    return GraphResult(
        nodes=svg_nodes,
        edges=svg_edges,
        branch_headers=svg_headers,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )


def _dummy_commit(h: str) -> Commit:
    """SVG 変換用のダミー Commit オブジェクトを生成する。"""
    return Commit(
        hash=h,
        short_hash=h[:7] if len(h) >= 7 else h,
        message="",
        author_name="",
        author_email="",
        committed_at=0,
        repo_id="",
    )
```

注意: `SvgNode.commit` には実際の Commit オブジェクトが必要。`build_grid()` は commits リストを受け取るので、`to_svg` に commits を渡して hash で引けるようにする必要がある。`to_svg` のシグネチャを `to_svg(layout, commits)` に変更し、`build_grid` から渡す。

`build_grid()` も以下に更新する:

```python
def build_grid(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GraphResult:
    """グリッドエンジンでグラフを構築して GraphResult を返す。"""
    from backend.services.grid_coords import to_svg

    layout = build_layout(commits, parents, branches, tags, head_hash)
    return to_svg(layout, commits)
```

`to_svg` のシグネチャと `_dummy_commit` の処理を更新:

```python
def to_svg(layout: GridLayout, commits: list[Commit]) -> GraphResult:
    commit_map: dict[str, Commit] = {c.hash: c for c in commits}
    # ... 以下同様に commit_map[node.hash] で Commit を取得 ...
```

- [ ] **Step 2: 既存テストが壊れていないことを確認する**

```bash
uv run task test
```

Expected: 全テスト PASS

- [ ] **Step 3: コミットする**

```bash
git add backend/services/grid_coords.py backend/services/grid_builder.py
git commit -m "feat: grid_coords.py で SVG 変換を実装する"
```

---

## Task 15: ルーターを新エンジンに切り替える

**Files:**
- Modify: `backend/routers/html.py`

- [ ] **Step 1: html.py の import を変更する**

`backend/routers/html.py` を開き、以下の行を探す:

```python
from backend.services import graph_builder
```

以下に変更する:

```python
from backend.services import grid_builder
```

- [ ] **Step 2: build_graph の呼び出しを build_grid に変更する**

同ファイル内の呼び出し箇所を変更する:

```python
# 変更前
result = graph_builder.build_graph(rows, parents, branches, tags, rec.cached_head)

# 変更後
result = grid_builder.build_grid(rows, parents, branches, tags, rec.cached_head)
```

- [ ] **Step 3: 全テストが通ることを確認する**

```bash
uv run task test
```

Expected: 全テスト PASS

- [ ] **Step 4: アプリを起動して目視確認する**

```bash
uv run task dev
```

ブラウザで `http://localhost:8000` を開き、適当なリポジトリのグラフ画面を表示する。コミットノードとエッジが描画されることを確認する。

- [ ] **Step 5: コミットする**

```bash
git add backend/routers/html.py
git commit -m "feat: グラフエンジンをグリッド方式に切り替える"
```

---

## 完了チェックリスト

- [ ] `uv run task test` が全て PASS
- [ ] `uv run task typecheck` がエラーなし
- [ ] `uv run task lint` がエラーなし
- [ ] アプリ起動でグラフが描画される
- [ ] 既存 gitup コード（`graph_builder*.py`）が変更されていない
