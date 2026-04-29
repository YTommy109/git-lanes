# Fix Graph Line Crossing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `commit_to_node` にダミーノードが混入することで発生するノード重複・エッジ不整合を修正し、グラフのライン交差を解消する。

**Architecture:** GitUp の `_mapping`（非ダミーのみ格納）と同等の動作を Python の `commit_to_node` で実現する。`_place_parent` と `_realize_dummy` の「既存ノード再利用条件」に `not existing.dummy and existing.layer is curr` を追加するだけで達成できる。

**Tech Stack:** Python 3.12、pytest、`backend/services/graph_builder_helpers.py`

---

## バグの概要

**発生条件：** あるコミット X が (a) 前レイヤーにダミーとして存在し、(b) 別の実ノードの親でもある場合。

**旧動作（バグあり）:**
1. `_place_parent('X', ...)` → `commit_to_node['X']` = 前レイヤーのダミー → ダミーを `line.nodes` に追加してしまう（curr に実ノードを追加しない）
2. `_realize_dummy(dummy_X, curr, ...)` → 同一コミットの別ノードを curr に追加 → `commit_to_node['X']` を上書き

結果: 同一コミットに複数の SVG ノードが生成される。エッジの描画先座標がずれ、視覚的なライン交差が発生する。

**GitUp との対応:**
- `MAP_COMMIT_TO_NODE` は非ダミーのみを返す
- ダミーを処理するとき既に curr に非ダミーがあれば再利用（`XLOG_DEBUG_CHECK(node.layer == layer)` で検証）

---

## 変更ファイル

| 操作 | ファイル |
|------|---------|
| Modify | `backend/services/graph_builder_helpers.py` |
| Test | `tests/unit/test_graph_builder.py` |

---

### Task 1: `_place_parent` の条件修正テストを書く

**Files:**
- Test: `tests/unit/test_graph_builder.py`

- [ ] **Step 1: 失敗するテストを追加する**

`test_graph_builder.py` のファイル末尾に以下を追記する。

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py::test_build_graph_共通祖先コミットの重複がない -v
```

期待: `FAILED` または `AssertionError`（重複が検出される）

---

### Task 2: `_realize_dummy` の条件修正テストを書く

**Files:**
- Test: `tests/unit/test_graph_builder.py`

- [ ] **Step 1: 失敗するテストを追加する**

Task 1 のテストの直後に追記する。

```python
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
    # エッジの正規化（(child, parent) ペア）
    edge_pairs = {(e.d.split()[1], e.d.split()[4]) for e in result.edges}  # "M x1 y1 L x2 y2"
    # 各コミットへのエッジが 1 本ずつ（A は 2 本が正常）
    a_node = next(n for n in result.nodes if n.commit.hash == "a" * 40)
    edges_to_a = [e for e in result.edges if f"{a_node.cx:.1f} {a_node.cy:.1f}" in e.d]
    assert len(edges_to_a) == 2, f"A へのエッジ数が異常: {len(edges_to_a)}"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py::test_build_graph_ダイアモンドマージでエッジ数が正しい -v
```

期待: `FAILED` または `AssertionError`

---

### Task 3: `_place_parent` を修正する

**Files:**
- Modify: `backend/services/graph_builder_helpers.py:31-52`

- [ ] **Step 1: `_place_parent` の再利用条件を修正する**

`backend/services/graph_builder_helpers.py` の `_place_parent` 関数を以下に置き換える。

```python
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
    if existing and not existing.dummy and existing.layer is curr:
        # 同一レイヤーに非ダミーノードが既存 → 別パスが先に確定済み（GitUp と同等）
        line.nodes.append(existing)
    elif ph in commit_map:
        ready = _is_ready(ph, curr, commit_to_node, children_map)
        pnode = GraphNode(commit=commit_map[ph], layer=curr, primary_line=line, dummy=not ready)
        line.nodes.append(pnode)
        curr.nodes.append(pnode)
        commit_to_node[ph] = pnode
```

- [ ] **Step 2: Task 1 のテストがパスすることを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py::test_build_graph_共通祖先コミットの重複がない -v
```

期待: `PASSED`

---

### Task 4: `_realize_dummy` を修正する

**Files:**
- Modify: `backend/services/graph_builder_helpers.py:55-71`

- [ ] **Step 1: `_realize_dummy` に curr 内非ダミー確認を追加する**

`backend/services/graph_builder_helpers.py` の `_realize_dummy` 関数を以下に置き換える。

```python
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
```

- [ ] **Step 2: Task 1・Task 2 のテストが両方パスすることを確認する**

```bash
uv run task test tests/unit/test_graph_builder.py::test_build_graph_共通祖先コミットの重複がない tests/unit/test_graph_builder.py::test_build_graph_ダイアモンドマージでエッジ数が正しい -v
```

期待: 両方 `PASSED`

---

### Task 5: 全単体テストをパスさせてコミットする

**Files:**
- Modify: `backend/services/graph_builder_helpers.py`
- Test: `tests/unit/test_graph_builder.py`

- [ ] **Step 1: 全単体テストが通ることを確認する**

```bash
uv run task test tests/unit/ -v
```

期待: 全テスト `PASSED`

- [ ] **Step 2: lint・format チェック**

```bash
uv run task lint && uv run task format
```

- [ ] **Step 3: コミット**

```bash
git add backend/services/graph_builder_helpers.py tests/unit/test_graph_builder.py
git commit -m "fix: ダミーノード混入によるグラフライン交差を解消する

commit_to_node にダミーノードが格納されることで _place_parent が
前レイヤーのダミーを誤再利用し、同一コミットのノードが重複していた。
GitUp の _mapping（非ダミーのみ格納）と同等の動作になるよう
_place_parent と _realize_dummy の再利用条件に
'not existing.dummy and existing.layer is curr' を追加した。"
```
