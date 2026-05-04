# キーボードナビゲーション 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** コミットグラフのノードを矢印キーで移動・選択できるようにする

**Architecture:** `SvgNode` に `lane`/`row` フィールドを追加してテンプレートで `data-lane`/`data-row` 属性として出力し、`graph-keyboard.js` がそれらを参照してキーボードナビゲーションを実現する。既存の hyperscript クリックハンドラを `node.click()` で再利用するため、htmx や hyperscript の変更は不要。

**Tech Stack:** Python dataclass, Jinja2 template, Vanilla JS, pytest, Playwright

---

### Task 1: SvgNode に lane/row フィールドを追加する

**Files:**
- Modify: `backend/services/graph_models.py:37-45`
- Modify: `backend/services/grid_coords.py:84-92`
- Create: `tests/unit/test_svg_node_lane_row.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unit/test_svg_node_lane_row.py` を新規作成する:

```python
import datetime

from backend.models import Commit
from backend.services.grid_coords import to_svg
from backend.services.grid_models import GridLayout, GridNode

_REPO = "test-repo-id"


def _make_commit(hash: str, at: int = 0) -> Commit:
    return Commit(
        hash=hash,
        short_hash=hash[:7],
        message="テストコミット",
        author_name="Test",
        author_email="test@example.com",
        committed_at=at,
        repo_id=_REPO,
    )


def test_to_svg_assigns_lane_and_row_to_svg_node():
    # --- Arrange ---
    node = GridNode(hash="abc123a", lane=2, row=3, kind="commit", color="#ff0000")
    layout = GridLayout(nodes=[node])
    commits = [_make_commit("abc123a")]

    # --- Act ---
    result = to_svg(layout, commits, {})

    # --- Assert ---
    assert len(result.nodes) == 1
    svg_node = result.nodes[0]
    assert svg_node.lane == 2
    assert svg_node.row == 3


def test_to_svg_assigns_correct_lane_row_for_multiple_nodes():
    # --- Arrange ---
    nodes = [
        GridNode(hash="aaaaaaa", lane=0, row=0, kind="commit", color="#ff0000"),
        GridNode(hash="bbbbbbb", lane=1, row=1, kind="commit", color="#00ff00"),
        GridNode(hash="ccccccc", lane=0, row=2, kind="commit", color="#ff0000"),
    ]
    layout = GridLayout(nodes=nodes)
    commits = [
        _make_commit("aaaaaaa", at=2),
        _make_commit("bbbbbbb", at=1),
        _make_commit("ccccccc", at=0),
    ]

    # --- Act ---
    result = to_svg(layout, commits, {})

    # --- Assert ---
    node_by_hash = {n.commit.hash: n for n in result.nodes}
    assert node_by_hash["aaaaaaa"].lane == 0
    assert node_by_hash["aaaaaaa"].row == 0
    assert node_by_hash["bbbbbbb"].lane == 1
    assert node_by_hash["bbbbbbb"].row == 1
    assert node_by_hash["ccccccc"].lane == 0
    assert node_by_hash["ccccccc"].row == 2
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
uv run pytest tests/unit/test_svg_node_lane_row.py -v
```

期待: `AttributeError: 'SvgNode' has no attribute 'lane'` または `TypeError` で FAIL

- [ ] **Step 3: SvgNode に lane/row フィールドを追加する**

`backend/services/graph_models.py` の SvgNode クラスを修正する:

```python
@dataclass
class SvgNode:
    """SVG テンプレートへ渡すノード情報。"""

    cx: float
    cy: float
    lane: int
    row: int
    color: str
    commit: Commit
    labels: list[SvgLabel]
    node_type: NodeType = "regular"
```

- [ ] **Step 4: _build_svg_nodes() で lane/row を渡す**

`backend/services/grid_coords.py` の `SvgNode()` コンストラクタ呼び出し（行 84-92 付近）を修正する:

```python
result.append(
    SvgNode(
        cx=_cx(node.lane),
        cy=_cy(node.row),
        lane=node.lane,
        row=node.row,
        color=node.color,
        commit=commit,
        labels=_build_tag_labels(node.hash, node_type, tag_map),
        node_type=node_type,
    )
)
```

- [ ] **Step 5: 単体テストが全て通ることを確認する**

```bash
uv run pytest tests/unit/ -v
```

期待: 全テスト PASS（新規テスト 2 件を含む）

- [ ] **Step 6: コミットする**

```bash
git add backend/services/graph_models.py backend/services/grid_coords.py tests/unit/test_svg_node_lane_row.py
git commit -m "feat: SvgNode に lane/row フィールドを追加する"
```

---

### Task 2: テンプレートに data-lane/data-row 属性と SVG id を付与する

**Files:**
- Modify: `backend/templates/graph.html` (SVG 開始タグ行、commit-node の g 要素)

- [ ] **Step 1: SVG 要素に id を付与する**

`backend/templates/graph.html` の SVG 開始タグ（行 21 付近）を修正する。

変更前:
```html
<svg width="{{ svg_width }}" height="{{ svg_height }}"
```

変更後:
```html
<svg id="graph-svg" width="{{ svg_width }}" height="{{ svg_height }}"
```

- [ ] **Step 2: commit-node に data-lane/data-row を追加する**

`backend/templates/graph.html` の commit-node の `<g>` 要素（行 65 付近）を修正する。

変更前:
```html
  <g
    class="commit-node"
    data-msg="{{ node.commit.message.split('\n')[0] }}"
```

変更後:
```html
  <g
    class="commit-node"
    data-lane="{{ node.lane }}"
    data-row="{{ node.row }}"
    data-msg="{{ node.commit.message.split('\n')[0] }}"
```

- [ ] **Step 3: 統合テストが通ることを確認する**

```bash
uv run pytest tests/integration/ -v
```

期待: 全テスト PASS

- [ ] **Step 4: コミットする**

```bash
git add backend/templates/graph.html
git commit -m "feat: コミットノードに data-lane/data-row 属性を付与する"
```

---

### Task 3: graph-keyboard.js を実装してグラフに読み込む

**Files:**
- Create: `static/js/graph-keyboard.js`
- Modify: `backend/templates/graph.html` (script タグを追加)

- [ ] **Step 1: graph-keyboard.js を作成する**

`static/js/graph-keyboard.js` を新規作成する:

```javascript
/** コミットグラフのキーボードナビゲーション */

const NAV_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']);

function getCommitNodes() {
  return Array.from(document.querySelectorAll('.commit-node'));
}

function coords(node) {
  return {
    lane: parseInt(node.dataset.lane, 10),
    row: parseInt(node.dataset.row, 10),
  };
}

function findSelectedNode() {
  return document.querySelector('.commit-node.selected');
}

/** 同レーン内で delta 方向（+1=下, -1=上）の最近接ノードを返す */
function findVertical(nodes, lane, row, delta) {
  const candidates = nodes.filter((n) => {
    const c = coords(n);
    return c.lane === lane && (delta > 0 ? c.row > row : c.row < row);
  });
  if (!candidates.length) return null;
  return candidates.reduce((best, n) =>
    Math.abs(coords(n).row - row) < Math.abs(coords(best).row - row) ? n : best
  );
}

/** 指定レーンの中で currentRow に最も近いノードを返す */
function findNearestInLane(nodes, targetLane, currentRow) {
  const candidates = nodes.filter((n) => coords(n).lane === targetLane);
  if (!candidates.length) return null;
  return candidates.reduce((best, n) =>
    Math.abs(coords(n).row - currentRow) < Math.abs(coords(best).row - currentRow) ? n : best
  );
}

/** delta 方向の隣レーンに最近接ノードを探す（空レーンをスキップ） */
function findHorizontal(nodes, lane, row, delta) {
  const maxLane = Math.max(...nodes.map((n) => coords(n).lane));
  for (let offset = 1; offset <= maxLane + 1; offset++) {
    const target = lane + delta * offset;
    if (target < 0 || target > maxLane) break;
    const node = findNearestInLane(nodes, target, row);
    if (node) return node;
  }
  return null;
}

/** ↓で次ノードがない場合に intersect センチネルをスクロールさせ次ページロードを試みる */
function tryLoadNextPage(lane, row) {
  const sentinel = document.querySelector('[hx-trigger*="intersect"]');
  if (!sentinel) return;
  sentinel.scrollIntoView({ behavior: 'smooth' });
  document.body.addEventListener(
    'htmx:afterSettle',
    () => {
      const node = findVertical(getCommitNodes(), lane, row, 1);
      if (node) selectNode(node);
    },
    { once: true }
  );
}

function selectNode(node) {
  node.click();
  node.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function navigate(key) {
  const nodes = getCommitNodes();
  if (!nodes.length) return;

  const selected = findSelectedNode();
  if (!selected) {
    selectNode(nodes[0]);
    return;
  }

  const { lane, row } = coords(selected);
  let target = null;

  if (key === 'ArrowUp') target = findVertical(nodes, lane, row, -1);
  else if (key === 'ArrowDown') {
    target = findVertical(nodes, lane, row, 1);
    if (!target) tryLoadNextPage(lane, row);
  } else if (key === 'ArrowLeft') target = findHorizontal(nodes, lane, row, -1);
  else if (key === 'ArrowRight') target = findHorizontal(nodes, lane, row, 1);

  if (target) selectNode(target);
}

document.addEventListener('keydown', (event) => {
  if (!document.querySelector('#graph-svg')) return;
  if (document.activeElement?.tagName === 'INPUT') return;

  if (event.key === ' ') {
    const selected = findSelectedNode();
    if (selected) {
      event.preventDefault();
      selected.click();
    }
    return;
  }

  if (!NAV_KEYS.has(event.key)) return;
  event.preventDefault();
  navigate(event.key);
});
```

- [ ] **Step 2: graph.html の `</body>` 直前に script タグを追加する**

`backend/templates/graph.html` の末尾（`</body>` の直前）を修正する。

変更前:
```html
</body>
</html>
```

変更後:
```html
<script src="/static/js/graph-keyboard.js"></script>
</body>
</html>
```

- [ ] **Step 3: lint を通す**

```bash
uv run task lint
uv run task typecheck
```

期待: エラーなし

- [ ] **Step 4: コミットする**

```bash
git add static/js/graph-keyboard.js backend/templates/graph.html
git commit -m "feat: キーボードナビゲーションを実装する"
```

---

### Task 4: E2E テストを書く

**Files:**
- Create: `tests/e2e/test_keyboard_navigation.py`

- [ ] **Step 1: E2E テストを作成する**

`tests/e2e/test_keyboard_navigation.py` を新規作成する:

```python
from playwright.sync_api import Page


def test_下キーで最初のノードが選択される(page: Page, base_url: str):
    # Given: グラフ画面が表示されている状態
    page.goto(f"{base_url}/repos/1/graph")
    page.wait_for_selector(".commit-node")

    # When: 下キーを押す
    page.keyboard.press("ArrowDown")

    # Then: いずれかのコミットノードが選択される
    page.wait_for_selector(".commit-node.selected")
    assert page.locator(".commit-node.selected").count() == 1


def test_下キーで同レーンの次コミットに移動する(page: Page, base_url: str):
    # Given: グラフ画面を開いて最初のノードを選択した状態
    page.goto(f"{base_url}/repos/1/graph")
    page.wait_for_selector(".commit-node")
    page.keyboard.press("ArrowDown")
    page.wait_for_selector(".commit-node.selected")

    first = page.locator(".commit-node.selected").first
    first_lane = first.get_attribute("data-lane")
    first_row = int(first.get_attribute("data-row"))

    # When: さらに下キーを押す
    page.keyboard.press("ArrowDown")

    # Then: 同じレーンの次の行のコミットが選択される
    selected = page.locator(".commit-node.selected").first
    assert selected.get_attribute("data-lane") == first_lane
    assert int(selected.get_attribute("data-row")) > first_row


def test_右キーで隣レーンのコミットに移動する(page: Page, base_url: str):
    # Given: グラフ画面を開いてノードを選択した状態
    page.goto(f"{base_url}/repos/1/graph")
    page.wait_for_selector(".commit-node")
    page.keyboard.press("ArrowDown")
    page.wait_for_selector(".commit-node.selected")
    initial_lane = int(
        page.locator(".commit-node.selected").first.get_attribute("data-lane")
    )

    # When: 右キーを押す
    page.keyboard.press("ArrowRight")

    # Then: より大きいレーン番号のコミットが選択される
    selected_lane = int(
        page.locator(".commit-node.selected").first.get_attribute("data-lane")
    )
    assert selected_lane > initial_lane


def test_スペースキーでコミット詳細が表示される(page: Page, base_url: str):
    # Given: コミットが選択されている状態
    page.goto(f"{base_url}/repos/1/graph")
    page.wait_for_selector(".commit-node")
    page.keyboard.press("ArrowDown")
    page.wait_for_selector(".commit-node.selected")

    # When: スペースキーを押す
    page.keyboard.press("Space")

    # Then: コミット詳細パネルに内容が表示される
    page.wait_for_function(
        "document.querySelector('#commit-detail') && "
        "document.querySelector('#commit-detail').textContent.trim().length > 0"
    )
    detail = page.locator("#commit-detail").text_content()
    assert detail and len(detail.strip()) > 0
```

- [ ] **Step 2: E2E テストを実行して通ることを確認する**

```bash
uv run task test:e2e tests/e2e/test_keyboard_navigation.py -v
```

期待: 全テスト PASS

- [ ] **Step 3: コミットする**

```bash
git add tests/e2e/test_keyboard_navigation.py
git commit -m "test: キーボードナビゲーションの E2E テストを追加する"
```
