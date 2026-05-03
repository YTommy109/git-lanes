# タグ表示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** コミットノードおよびブランチヘッダーに Git タグを表示する（ケース 13 / 14 / 15）

**Architecture:**
`build_layout()` でブランチ tip のタグを `GridBranchLabel.names` に `[tagname]` 形式で追記し、`to_svg()` で非 tip コミットのタグを `SvgNode.labels` に追加する。
`build_grid()` がタグを `to_svg()` に渡す橋渡し役を担う。
テンプレート側のタグバッジ色は仕様（`#333333`）に合わせて修正する。

**Tech Stack:** Python 3.12 / SQLModel / Jinja2 / pytest

---

## ファイル一覧

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `backend/services/grid_builder.py` | 修正 | `_build_tag_map()` 追加・`build_layout()` と `build_grid()` でタグを渡す |
| `backend/services/grid_builder_utils.py` | 修正 | `_build_branch_labels()` に `tag_map` 引数を追加してブランチ tip のタグを名前リストへ挿入 |
| `backend/services/grid_coords.py` | 修正 | `to_svg()` / `_build_svg_nodes()` に `tag_map` を追加し非 tip ノードのラベルを生成 |
| `backend/templates/graph.html` | 修正 | タグバッジの `stroke` / `fill` を `#888` → `#333333`、`rx` を `7` → `3`、`font-size` を `11` → `10` に修正 |
| `tests/unit/test_grid_builder.py` | 修正 | `_t()` ヘルパーとケース 13 / 14 / 15 のテストを追加 |

---

## Task 1: ケース 15 テストを書いて失敗させる

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

- [ ] **Step 1: `_t()` ヘルパーと失敗テストを追加する**

`test_grid_builder.py` の `_p()` 関数の直後に以下を追加する。

```python
from backend.models import Tag


def _t(name: str, commit_hash: str) -> Tag:
    """テスト用 Tag を生成する。"""
    return Tag(name=name, repo_id=_REPO, commit_hash=commit_hash)


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
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```
uv run pytest tests/unit/test_grid_builder.py::test_ケース15_ブランチtipにタグが付いている -v
```

期待: `FAILED`（`[v1.0]` が names に存在しない）

---

## Task 2: `_build_branch_labels()` に `tag_map` を追加してケース 15 を通す

**Files:**
- Modify: `backend/services/grid_builder_utils.py`
- Modify: `backend/services/grid_builder.py`

- [ ] **Step 1: `grid_builder_utils.py` の `_build_branch_labels()` を修正する**

関数シグネチャに `tag_map` を追加し、ブランチ tip のタグを `[tagname]` 形式で `names` に追記する。

```python
def _build_branch_labels(
    branches: list[Branch],
    tip_lane: dict[str, int],
    color_map: dict[str, str],
    placed: dict[str, GridNode],
    tag_map: dict[str, list[str]],
) -> list[GridBranchLabel]:
    """ブランチラベルリストを構築する。

    Args:
        branches: ブランチのリスト。
        tip_lane: ブランチ tip からレーン番号へのマップ。
        color_map: ブランチ名から色へのマップ。
        placed: 配置済みコミットのマップ。
        tag_map: コミットハッシュからタグ名リストへのマップ。

    Returns:
        GridBranchLabel のリスト。
    """
    lane_to_names: dict[int, list[str]] = {}
    lane_to_color: dict[int, str] = {}
    for b in branches:
        tip_h = b.tip_hash
        if tip_h in placed and placed[tip_h].row == 0:
            target_lane = placed[tip_h].lane
        else:
            target_lane = tip_lane.get(tip_h)
        if target_lane is None:
            continue
        lane_to_names.setdefault(target_lane, []).append(b.name)
        lane_to_color[target_lane] = color_map.get(b.name, GRID_COLORS[0])
        for tag_name in tag_map.get(tip_h, []):
            lane_to_names[target_lane].append(f"[{tag_name}]")
    return [
        GridBranchLabel(lane=ln, names=names, color=lane_to_color[ln])
        for ln, names in lane_to_names.items()
    ]
```

- [ ] **Step 2: `grid_builder.py` に `_build_tag_map()` を追加し、`build_layout()` で使う**

`build_layout()` の上に `_build_tag_map()` を追加し、`build_layout()` 内で呼び出す。

`grid_builder.py` の `_place_commits()` 関数の上に以下を追加する：

```python
def _build_tag_map(tags: list[Tag]) -> dict[str, list[str]]:
    """タグリストをコミットハッシュ→タグ名リストの辞書に変換する。"""
    result: dict[str, list[str]] = {}
    for tag in tags:
        result.setdefault(tag.commit_hash, []).append(tag.name)
    return result
```

`build_layout()` 内の `_build_branch_labels()` 呼び出しを変更する：

```python
    tag_map = _build_tag_map(tags)
    for label in _build_branch_labels(branches, tip_lane, color_map, placed, tag_map):
        layout.branch_labels.append(label)
```

また `build_layout()` のドックストリングから `# tags は今後タグラベル表示に使用予定` コメントを削除する。

- [ ] **Step 3: テストを実行して通ることを確認する**

```
uv run pytest tests/unit/test_grid_builder.py::test_ケース15_ブランチtipにタグが付いている -v
```

期待: `PASSED`

- [ ] **Step 4: 既存テストが壊れていないことを確認する**

```
uv run pytest tests/unit/test_grid_builder.py -v
```

期待: 全テスト `PASSED`

- [ ] **Step 5: コミットする**

```bash
git add backend/services/grid_builder.py backend/services/grid_builder_utils.py tests/unit/test_grid_builder.py
git commit -m "feat: ブランチ tip のタグをヘッダーラベルに表示する（ケース 15）"
```

---

## Task 3: ケース 13 / 14 テストを書いて失敗させる

**Files:**
- Modify: `tests/unit/test_grid_builder.py`

- [ ] **Step 1: ケース 13 / 14 のテストを追加する**

`test_grid_builder.py` の末尾に以下を追加する。

```python
from backend.services.grid_builder import build_grid


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
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```
uv run pytest tests/unit/test_grid_builder.py::test_ケース13_コミットにタグが付いている tests/unit/test_grid_builder.py::test_ケース14_コミットにタグが2つ付いている -v
```

期待: 両テストとも `FAILED`（`labels` が空）

---

## Task 4: `to_svg()` に `tag_map` を渡してケース 13 / 14 を通す

**Files:**
- Modify: `backend/services/grid_coords.py`
- Modify: `backend/services/grid_builder.py`

- [ ] **Step 1: `grid_coords.py` の `to_svg()` と `_build_svg_nodes()` を修正する**

`to_svg()` のシグネチャに `tag_map` を追加し、`_build_svg_nodes()` に渡す。

```python
def to_svg(
    layout: GridLayout,
    commits: list[Commit],
    parents: dict[str, list[str]],
    tag_map: dict[str, list[str]] | None = None,
) -> GraphResult:
    """GridLayout を GraphResult に変換する。

    Args:
        layout: グリッドレイアウト（build_layout の返り値）。
        commits: コミットのリスト（SvgNode.commit に渡す）。
        parents: コミットハッシュ → 親ハッシュリスト のマップ。
        tag_map: コミットハッシュ → タグ名リストのマップ。非 tip コミットのバッジ表示に使う。

    Returns:
        SVG テンプレートへ渡す GraphResult。
    """
    commit_map: dict[str, Commit] = {c.hash: c for c in commits}
    svg_nodes = _build_svg_nodes(layout, commit_map, parents, tag_map or {})
    svg_edges = _build_svg_edges(layout)
    svg_headers = _build_svg_headers(layout)
    canvas_width, canvas_height = _calc_canvas(layout)
    return GraphResult(
        nodes=svg_nodes,
        edges=svg_edges,
        branch_headers=svg_headers,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )
```

`_build_svg_nodes()` のシグネチャと本体を修正する。

```python
def _build_svg_nodes(
    layout: GridLayout,
    commit_map: dict[str, Commit],
    parents: dict[str, list[str]],
    tag_map: dict[str, list[str]],
) -> list[SvgNode]:
    """GridNode リストを SvgNode リストに変換する。"""
    result: list[SvgNode] = []
    for node in layout.nodes:
        if node.kind == "joint":
            continue
        if node.hash is None:
            continue
        commit = commit_map.get(node.hash)
        if commit is None:
            continue
        node_parents = parents.get(node.hash, [])
        if len(node_parents) == 0:
            node_type: NodeType = "root"
        elif len(node_parents) >= 2:
            node_type = "merge"
        elif node.row == 0:
            node_type = "tip"
        else:
            node_type = "regular"
        # tip ノードのタグはヘッダー行に表示するため、バッジは付けない
        labels: list[SvgLabel] = []
        if node_type != "tip":
            tag_names = tag_map.get(node.hash, [])
            if tag_names:
                labels.append(SvgLabel(text=", ".join(tag_names), kind="tag"))
        result.append(
            SvgNode(
                cx=_cx(node.lane),
                cy=_cy(node.row),
                color=node.color,
                commit=commit,
                labels=labels,
                node_type=node_type,
            )
        )
    return result
```

- [ ] **Step 2: `grid_builder.py` の `build_grid()` を修正して `tag_map` を `to_svg()` に渡す**

```python
def build_grid(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GraphResult:
    """グリッドエンジンでグラフを構築して GraphResult を返す。

    Args:
        commits: コミットのリスト（新しい順）。
        parents: コミットハッシュ → 親ハッシュリスト のマップ。
        branches: ブランチのリスト。
        tags: タグのリスト。
        head_hash: HEAD コミットのハッシュ（今後使用予定）。

    Returns:
        SVG テンプレートへ渡す GraphResult。
    """
    from backend.services.grid_coords import to_svg

    tag_map = _build_tag_map(tags)
    layout = build_layout(commits, parents, branches, tags, head_hash)
    return to_svg(layout, commits, parents, tag_map)
```

- [ ] **Step 3: テストを実行して通ることを確認する**

```
uv run pytest tests/unit/test_grid_builder.py::test_ケース13_コミットにタグが付いている tests/unit/test_grid_builder.py::test_ケース14_コミットにタグが2つ付いている -v
```

期待: 両テストとも `PASSED`

- [ ] **Step 4: 全テストが通ることを確認する**

```
uv run pytest tests/unit/test_grid_builder.py -v
```

期待: 全テスト `PASSED`

- [ ] **Step 5: コミットする**

```bash
git add backend/services/grid_coords.py backend/services/grid_builder.py tests/unit/test_grid_builder.py
git commit -m "feat: 非 tip コミットのタグをノードバッジに表示する（ケース 13 / 14）"
```

---

## Task 5: テンプレートのタグバッジスタイルを仕様に合わせる

**Files:**
- Modify: `backend/templates/graph.html`

- [ ] **Step 1: タグバッジの `stroke` / `fill` / `rx` / `font-size` を修正する**

`graph.html` のタグバッジ描画部分（`label.kind == "tag"` ブロック）を以下に変更する。

変更前:
```html
{% elif label.kind == "tag" %}
  <rect x="{{ node.cx + 12 + ns.x_offset }}" y="{{ node.cy - 8 }}"
        width="{{ badge_width }}" height="16"
        rx="7" fill="none" stroke="#888" stroke-width="1" pointer-events="none"/>
  <text x="{{ node.cx + 16 + ns.x_offset }}" y="{{ node.cy + 4 }}"
        font-size="11" fill="#888" pointer-events="none">{{ label.text }}</text>
```

変更後:
```html
{% elif label.kind == "tag" %}
  <rect x="{{ node.cx + 12 + ns.x_offset }}" y="{{ node.cy - 8 }}"
        width="{{ badge_width }}" height="16"
        rx="3" fill="none" stroke="#333333" stroke-width="1" pointer-events="none"/>
  <text x="{{ node.cx + 16 + ns.x_offset }}" y="{{ node.cy + 4 }}"
        font-size="10" fill="#333333" pointer-events="none">{{ label.text }}</text>
```

- [ ] **Step 2: 全テストが通ることを確認する**

```
uv run pytest tests/unit/ -v
```

期待: 全テスト `PASSED`

- [ ] **Step 3: lint / typecheck を通す**

```
uv run task lint && uv run task typecheck
```

期待: エラーなし

- [ ] **Step 4: コミットする**

```bash
git add backend/templates/graph.html
git commit -m "fix: タグバッジのスタイルを仕様（#333333・rx=3・font-size=10）に合わせる"
```
