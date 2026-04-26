# マルチレーングラフ 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitUp スタイルのマルチレーングラフを実装する。各ブランチが独立した縦レーンを持ち、接続線の交差を最小化する。

**Architecture:** Python 側でレーン割り当てを計算して `LayoutNode`/`BranchLane` を生成し、Jinja2 テンプレートが SVG を描画する。ヘルパー関数は `lane_assignment.py` に分離して `graph_layout.py` の行数制限を守る。

**Tech Stack:** Python 3.12+, FastAPI, SQLModel, Jinja2, htmx, pygit2

---

## ファイル構成

| 操作 | ファイル | 内容 |
| --- | --- | --- |
| 新規作成 | `backend/services/lane_assignment.py` | レーン計算ヘルパー関数群 |
| 新規作成 | `tests/unit/test_lane_assignment.py` | ヘルパーの単体テスト |
| 修正 | `backend/services/graph_layout.py` | `BranchLane`・`LANE_COLORS`・`build_multi_lane_layout` 追加、`LayoutNode` に `lane` フィールド追加 |
| 修正 | `tests/unit/test_graph_layout.py` | `build_multi_lane_layout` のテスト追加 |
| 修正 | `backend/repositories/cache_repo.py` | `list_branches` 追加 |
| 修正 | `tests/unit/test_cache_repo.py` | `list_branches` のテスト追加 |
| 修正 | `backend/routers/html.py` | `build_multi_lane_layout` を呼び出すよう変更 |
| 修正 | `backend/templates/graph.html` | マルチレーン SVG 描画に対応 |
| 修正 | `tests/e2e/test_graph_smoke.py` | マルチレーン表示の確認を追加 |
| 修正 | `tests/support/git_repo_fixture.py` | マルチブランチ fixture 追加 |

---

## Task 1: `list_branches` を cache_repo に追加する

**Files:**
- Modify: `backend/repositories/cache_repo.py`
- Modify: `tests/unit/test_cache_repo.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/unit/test_cache_repo.py` の末尾に追加する:

```python
# ── list_branches ──────────────────────────────────────────

def test_list_branches_登録済みブランチを返す(session):
    # --- Arrange ---
    _add_repo(session)
    _add_commit(session, "r1", "a" * 40)
    cache_repo.insert_branch_row(session, "r1", "main", "a" * 40, 0)
    cache_repo.insert_branch_row(session, "r1", "feat/x", "a" * 40, 0)
    session.commit()

    # --- Act ---
    result = cache_repo.list_branches(session, "r1")

    # --- Assert ---
    assert {b.name for b in result} == {"main", "feat/x"}


def test_list_branches_ブランチなしは空リスト(session):
    # --- Arrange ---
    _add_repo(session)

    # --- Act ---
    result = cache_repo.list_branches(session, "r1")

    # --- Assert ---
    assert result == []
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_cache_repo.py::test_list_branches_登録済みブランチを返す -v
```

期待: `AttributeError: module 'backend.repositories.cache_repo' has no attribute 'list_branches'`

- [ ] **Step 3: `list_branches` を実装する**

`backend/repositories/cache_repo.py` の `insert_branch_row` の前に追加する:

```python
def list_branches(session: Session, repo_id: str) -> list[Branch]:
    """リポジトリの全ブランチを返す。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。

    Returns:
        Branch のリスト。
    """
    return list(
        session.exec(select(Branch).where(Branch.repo_id == repo_id)).all()
    )
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_cache_repo.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: コミットする**

```bash
git add backend/repositories/cache_repo.py tests/unit/test_cache_repo.py
git commit -m "feat: list_branches を cache_repo に追加する"
```

---

## Task 2: データクラスと定数を graph_layout.py に追加する

**Files:**
- Modify: `backend/services/graph_layout.py`
- Modify: `tests/unit/test_graph_layout.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/unit/test_graph_layout.py` の末尾に追加する:

```python
from backend.services.graph_layout import BranchLane, LANE_COLORS
from backend.models import Branch


def _make_commit(hash_prefix: str, at: int) -> Commit:
    """テスト用 Commit を生成する。"""
    h = hash_prefix * 40
    return Commit(
        hash=h,
        short_hash=h[:7],
        message="msg",
        author_name="a",
        author_email="a@b.c",
        committed_at=at,
        repo_id=_REPO_ID,
    )


def _make_branch(name: str, tip_prefix: str) -> Branch:
    """テスト用 Branch を生成する。"""
    return Branch(name=name, repo_id=_REPO_ID, tip_hash=tip_prefix * 40, is_remote=0)


def test_LANE_COLORS_は8色():
    assert len(LANE_COLORS) == 8


def test_BranchLane_は必須フィールドを持つ():
    # --- Arrange / Act ---
    bl = BranchLane(
        name="main",
        lane=0,
        tip_hash="a" * 40,
        has_unique_commits=True,
        connect_hash="a" * 40,
        x=36.0,
    )

    # --- Assert ---
    assert bl.lane == 0
    assert bl.x == 36.0
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_graph_layout.py::test_LANE_COLORS_は8色 -v
```

期待: `ImportError`

- [ ] **Step 3: `BranchLane`・`LANE_COLORS`・定数を graph_layout.py に追加する**

`backend/services/graph_layout.py` の `LayoutEdge` の後に追加する:

```python
LANE_COLORS: list[str] = [
    "#e05555",  # 0: main
    "#e67e22",  # 1
    "#2ecc71",  # 2
    "#3498db",  # 3
    "#9b59b6",  # 4
    "#1abc9c",  # 5
    "#f1c40f",  # 6
    "#e91e63",  # 7
]

LANE_WIDTH = 70.0
LANE_OFFSET = 36.0
ROW_SPACING = 60.0
MARGIN_TOP = 145.0


@dataclass(frozen=True)
class BranchLane:
    """ブランチのレーン情報。"""

    name: str
    lane: int
    tip_hash: str
    has_unique_commits: bool
    connect_hash: str
    x: float
```

また、`LayoutNode` に `lane` フィールドを追加する（デフォルト 0 で既存コードを壊さない）:

```python
@dataclass(frozen=True)
class LayoutNode:
    """レイアウト済みノード。"""

    commit: Commit
    x: float
    y: float
    lane: int = 0
```

`graph_layout.py` のインポートに `Branch` を追加する:

```python
from backend.models import Branch, Commit
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_graph_layout.py -v
```

期待: 全テスト PASS（既存テストも含む）

- [ ] **Step 5: コミットする**

```bash
git add backend/services/graph_layout.py tests/unit/test_graph_layout.py
git commit -m "feat: BranchLane・LANE_COLORS・定数を graph_layout に追加する"
```

---

## Task 3: `lane_assignment.py` にヘルパー関数を実装する

**Files:**
- Create: `backend/services/lane_assignment.py`
- Create: `tests/unit/test_lane_assignment.py`

- [ ] **Step 1: 失敗テストを書く**

新規ファイル `tests/unit/test_lane_assignment.py` を作成する:

```python
"""lane_assignment ヘルパーの単体テスト。"""

from backend.models import Branch, Commit
from backend.services.lane_assignment import (
    _find_connect_hash,
    _find_main_hashes,
)

_REPO_ID = "r1"


def _c(prefix: str, at: int = 0) -> Commit:
    h = prefix * 40
    return Commit(
        hash=h, short_hash=h[:7], message="m", author_name="a",
        author_email="a@b.c", committed_at=at, repo_id=_REPO_ID,
    )


def _b(name: str, tip_prefix: str) -> Branch:
    return Branch(name=name, repo_id=_REPO_ID, tip_hash=tip_prefix * 40, is_remote=0)


# ── _find_main_hashes ──────────────────────────────────────


def test_find_main_hashes_直線履歴は全コミットを返す():
    # --- Arrange ---
    rows = [_c("c", 3), _c("b", 2), _c("a", 1)]
    parents = {"c" * 40: ["b" * 40], "b" * 40: ["a" * 40]}
    row_set = {r.hash for r in rows}

    # --- Act ---
    result = _find_main_hashes("c" * 40, parents, row_set)

    # --- Assert ---
    assert result == {"c" * 40, "b" * 40, "a" * 40}


def test_find_main_hashes_マージコミットは第1親のみ辿る():
    # --- Arrange ---
    # main: c → b → a
    # feat: d → b (d は main 外)
    rows = [_c("c", 4), _c("d", 3), _c("b", 2), _c("a", 1)]
    parents = {
        "c" * 40: ["b" * 40, "d" * 40],  # c は b(第1親) と d(第2親) を持つマージ
        "d" * 40: ["b" * 40],
        "b" * 40: ["a" * 40],
    }
    row_set = {r.hash for r in rows}

    # --- Act ---
    result = _find_main_hashes("c" * 40, parents, row_set)

    # --- Assert ---
    assert result == {"c" * 40, "b" * 40, "a" * 40}
    assert "d" * 40 not in result


def test_find_main_hashes_visible外は含めない():
    # --- Arrange ---
    rows = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40], "a" * 40: ["z" * 40]}  # z は visible 外
    row_set = {r.hash for r in rows}

    # --- Act ---
    result = _find_main_hashes("b" * 40, parents, row_set)

    # --- Assert ---
    assert result == {"b" * 40, "a" * 40}
    assert "z" * 40 not in result


# ── _find_connect_hash ─────────────────────────────────────


def test_find_connect_hash_ブランチが直接mainのコミットを指す():
    # --- Arrange ---
    main_hashes = {"b" * 40, "a" * 40}
    row_set = {"c" * 40, "b" * 40, "a" * 40}
    parents = {"c" * 40: ["b" * 40]}

    # --- Act ---
    result = _find_connect_hash("c" * 40, parents, main_hashes, row_set, "a" * 40)

    # --- Assert ---
    assert result == "b" * 40


def test_find_connect_hash_tip自体がmain上はtipを返す():
    # --- Arrange ---
    main_hashes = {"b" * 40, "a" * 40}
    row_set = {"b" * 40, "a" * 40}
    parents = {"b" * 40: ["a" * 40]}

    # --- Act ---
    result = _find_connect_hash("b" * 40, parents, main_hashes, row_set, "a" * 40)

    # --- Assert ---
    assert result == "b" * 40


def test_find_connect_hash_visible外はfallbackを返す():
    # --- Arrange ---
    main_hashes = {"a" * 40}
    row_set = {"c" * 40}  # b と a は visible 外
    parents = {"c" * 40: ["b" * 40]}
    fallback = "a" * 40

    # --- Act ---
    result = _find_connect_hash("c" * 40, parents, main_hashes, row_set, fallback)

    # --- Assert ---
    assert result == fallback
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_lane_assignment.py -v
```

期待: `ModuleNotFoundError`

- [ ] **Step 3: `lane_assignment.py` を作成して `_find_main_hashes` と `_find_connect_hash` を実装する**

新規ファイル `backend/services/lane_assignment.py` を作成する:

```python
"""レーン割り当てのヘルパー関数群。"""

from __future__ import annotations

from backend.models import Branch, Commit
from backend.services.graph_layout import (
    LANE_OFFSET,
    LANE_WIDTH,
    MARGIN_TOP,
    ROW_SPACING,
    BranchLane,
    LayoutEdge,
    LayoutNode,
)


def _find_main_hashes(
    tip_hash: str,
    parents: dict[str, list[str]],
    row_set: set[str],
) -> set[str]:
    """main の第1親チェーンに属するハッシュを収集する。

    Args:
        tip_hash: main ブランチの先端ハッシュ。
        parents: 子→親ハッシュのリスト辞書（position 順）。
        row_set: 表示対象コミットのハッシュ集合。

    Returns:
        main チェーン上のハッシュ集合。
    """
    result: set[str] = set()
    current: str | None = tip_hash
    while current and current in row_set:
        result.add(current)
        chain = parents.get(current, [])
        current = chain[0] if chain else None
    return result


def _find_connect_hash(
    tip_hash: str,
    parents: dict[str, list[str]],
    main_hashes: set[str],
    row_set: set[str],
    fallback: str,
) -> str:
    """ブランチ先端から第1親を辿り、main との接続点ハッシュを返す。

    Args:
        tip_hash: ブランチ先端のハッシュ。
        parents: 子→親ハッシュのリスト辞書。
        main_hashes: main チェーンのハッシュ集合。
        row_set: 表示対象コミットのハッシュ集合。
        fallback: visible 外に出た場合に返すハッシュ。

    Returns:
        main 上の接続点ハッシュ。
    """
    current: str | None = tip_hash
    while current and current in row_set:
        if current in main_hashes:
            return current
        chain = parents.get(current, [])
        current = chain[0] if chain else None
    return fallback


def _assign_lanes(
    branches: list[Branch],
    main_branch: Branch,
    parents: dict[str, list[str]],
    main_hashes: set[str],
    row_set: set[str],
    hash_to_row: dict[str, int],
    rows: list[Commit],
) -> list[BranchLane]:
    """main 以外のブランチにレーン番号を割り当てる。

    接続点の行インデックス昇順（= main 上で上に近い順）でソートして
    lane=1, 2, 3... を付与する。

    Args:
        branches: 全ブランチのリスト。
        main_branch: main として扱うブランチ。
        parents: 子→親ハッシュのリスト辞書。
        main_hashes: main チェーンのハッシュ集合。
        row_set: 表示対象コミットのハッシュ集合。
        hash_to_row: ハッシュ→行インデックスの辞書。
        rows: 表示対象コミットのリスト（降順）。

    Returns:
        main 以外の BranchLane のリスト（lane 順）。
    """
    fallback = rows[-1].hash if rows else ""
    items: list[tuple[int, str, str, str, bool, str]] = []
    for br in branches:
        if br.name == main_branch.name:
            continue
        connect = _find_connect_hash(
            br.tip_hash, parents, main_hashes, row_set, fallback
        )
        has_unique = br.tip_hash not in main_hashes
        row_idx = hash_to_row.get(connect, len(rows))
        items.append((row_idx, br.tip_hash, br.name, br.tip_hash, has_unique, connect))
    items.sort()
    return [
        BranchLane(
            name=name,
            lane=i + 1,
            tip_hash=tip,
            has_unique_commits=has_unique,
            connect_hash=connect,
            x=(i + 1) * LANE_WIDTH + LANE_OFFSET,
        )
        for i, (_, _, name, tip, has_unique, connect) in enumerate(items)
    ]


def _build_hash_to_lane(
    branch_lanes: list[BranchLane],
    parents: dict[str, list[str]],
    main_hashes: set[str],
    row_set: set[str],
) -> dict[str, int]:
    """各コミットハッシュのレーン番号を返す。

    main ハッシュは lane=0、各ブランチの固有コミットはそのブランチの lane。

    Args:
        branch_lanes: main 以外の BranchLane リスト。
        parents: 子→親ハッシュのリスト辞書。
        main_hashes: main チェーンのハッシュ集合。
        row_set: 表示対象コミットのハッシュ集合。

    Returns:
        ハッシュ→レーン番号の辞書。
    """
    result: dict[str, int] = {h: 0 for h in main_hashes}
    for bl in branch_lanes:
        if not bl.has_unique_commits:
            continue
        current: str | None = bl.tip_hash
        while current and current in row_set and current not in main_hashes:
            if current not in result:
                result[current] = bl.lane
            chain = parents.get(current, [])
            current = chain[0] if chain else None
    return result


def build_lane_nodes(
    rows: list[Commit],
    hash_to_lane: dict[str, int],
) -> list[LayoutNode]:
    """各コミットに座標とレーンを付与した LayoutNode リストを返す。

    Args:
        rows: 表示対象コミットのリスト（降順）。
        hash_to_lane: ハッシュ→レーン番号の辞書。

    Returns:
        LayoutNode のリスト。
    """
    nodes = []
    for i, commit in enumerate(rows):
        lane = hash_to_lane.get(commit.hash, 0)
        x = lane * LANE_WIDTH + LANE_OFFSET
        y = MARGIN_TOP + i * ROW_SPACING
        nodes.append(LayoutNode(commit=commit, x=x, y=y, lane=lane))
    return nodes


def build_lane_edges(
    rows: list[Commit],
    parents: dict[str, list[str]],
    row_set: set[str],
) -> list[LayoutEdge]:
    """visible set 内のエッジ一覧を返す。

    Args:
        rows: 表示対象コミットのリスト。
        parents: 子→親ハッシュのリスト辞書。
        row_set: 表示対象コミットのハッシュ集合。

    Returns:
        LayoutEdge のリスト。
    """
    edges = []
    for r in rows:
        for ph in parents.get(r.hash, []):
            if ph in row_set:
                edges.append(LayoutEdge(child_hash=r.hash, parent_hash=ph))
    return edges
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_lane_assignment.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: コミットする**

```bash
git add backend/services/lane_assignment.py tests/unit/test_lane_assignment.py
git commit -m "feat: lane_assignment ヘルパー関数を実装する"
```

---

## Task 4: `_assign_lanes` のテストを追加する

**Files:**
- Modify: `tests/unit/test_lane_assignment.py`

- [ ] **Step 1: `_assign_lanes` のテストを追加する**

`tests/unit/test_lane_assignment.py` のインポートブロックを以下に更新する:

```python
from backend.services.lane_assignment import (
    _assign_lanes,
    _find_connect_hash,
    _find_main_hashes,
)
```

そのままファイル末尾にテスト関数を追加する:

```python
def test_assign_lanes_接続点が上のブランチが内側レーン():
    # --- Arrange ---
    # main: c(row0) → b(row1) → a(row2)
    # feat/x: x → b (row1 で接続)
    # feat/y: y → a (row2 で接続)
    rows = [_c("c", 3), _c("b", 2), _c("a", 1)]
    parents = {
        "c" * 40: ["b" * 40],
        "b" * 40: ["a" * 40],
        "x" * 40: ["b" * 40],
        "y" * 40: ["a" * 40],
    }
    main_branch = _b("main", "c")
    branches = [main_branch, _b("feat/x", "x"), _b("feat/y", "y")]
    main_hashes = {"c" * 40, "b" * 40, "a" * 40}
    row_set = {r.hash for r in rows}
    hash_to_row = {r.hash: i for i, r in enumerate(rows)}

    # --- Act ---
    result = _assign_lanes(
        branches, main_branch, parents, main_hashes, row_set, hash_to_row, rows
    )

    # --- Assert ---
    names_by_lane = {bl.lane: bl.name for bl in result}
    assert names_by_lane[1] == "feat/x"  # row1 接続 → 内側
    assert names_by_lane[2] == "feat/y"  # row2 接続 → 外側


def test_assign_lanes_独自コミットなしはhas_unique_commits_false():
    # --- Arrange ---
    rows = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    main_branch = _b("main", "b")
    branches = [main_branch, _b("hotfix", "b")]  # hotfix は main の先端を指す
    main_hashes = {"b" * 40, "a" * 40}
    row_set = {r.hash for r in rows}
    hash_to_row = {r.hash: i for i, r in enumerate(rows)}

    # --- Act ---
    result = _assign_lanes(
        branches, main_branch, parents, main_hashes, row_set, hash_to_row, rows
    )

    # --- Assert ---
    assert len(result) == 1
    assert result[0].has_unique_commits is False
    assert result[0].connect_hash == "b" * 40
```

- [ ] **Step 2: テストを実行して通ることを確認する**

```bash
uv run pytest tests/unit/test_lane_assignment.py -v
```

期待: 全テスト PASS

- [ ] **Step 3: コミットする**

```bash
git add tests/unit/test_lane_assignment.py
git commit -m "test: _assign_lanes のテストを追加する"
```

---

## Task 5: `build_multi_lane_layout` を graph_layout.py に実装する

**Files:**
- Modify: `backend/services/graph_layout.py`
- Modify: `tests/unit/test_graph_layout.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/unit/test_graph_layout.py` の既存インポート行を以下に更新する:

```python
from backend.services.graph_layout import (
    BranchLane,
    LANE_COLORS,
    build_multi_lane_layout,
    build_single_lane_layout,
)
```

ファイル末尾にテスト関数を追加する:

```python
def test_build_multi_lane_layout_mainのみのリポジトリ():
    # --- Arrange ---
    rows = [_make_commit("b", 2), _make_commit("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    branches = [_make_branch("main", "b")]

    # --- Act ---
    nodes, edges, branch_lanes = build_multi_lane_layout(rows, parents, branches)

    # --- Assert ---
    assert len(nodes) == 2
    assert len(edges) == 1
    assert len(branch_lanes) == 1
    assert branch_lanes[0].lane == 0
    assert all(n.lane == 0 for n in nodes)


def test_build_multi_lane_layout_ブランチ接続点ソートでレーン割り当て():
    # --- Arrange ---
    # main: c(row0) → b(row1) → a(row2)
    # feat/x tip=x → 接続 b(row1)  → lane=1
    # feat/y tip=y → 接続 a(row2)  → lane=2
    rows = [_make_commit("c", 3), _make_commit("b", 2), _make_commit("a", 1)]
    parents = {
        "c" * 40: ["b" * 40],
        "b" * 40: ["a" * 40],
        "x" * 40: ["b" * 40],
        "y" * 40: ["a" * 40],
    }
    branches = [
        _make_branch("main", "c"),
        _make_branch("feat/x", "x"),
        _make_branch("feat/y", "y"),
    ]

    # --- Act ---
    nodes, edges, branch_lanes = build_multi_lane_layout(rows, parents, branches)

    # --- Assert ---
    lane_map = {bl.name: bl.lane for bl in branch_lanes}
    assert lane_map["main"] == 0
    assert lane_map["feat/x"] == 1
    assert lane_map["feat/y"] == 2


def test_build_multi_lane_layout_空データは空を返す():
    # --- Act ---
    nodes, edges, branch_lanes = build_multi_lane_layout([], {}, [])

    # --- Assert ---
    assert nodes == []
    assert edges == []
    assert branch_lanes == []
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unit/test_graph_layout.py::test_build_multi_lane_layout_mainのみのリポジトリ -v
```

期待: `ImportError`

- [ ] **Step 3: `build_multi_lane_layout` を実装する**

`backend/services/graph_layout.py` の末尾に追加する:

```python
def build_multi_lane_layout(
    rows: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
) -> tuple[list[LayoutNode], list[LayoutEdge], list[BranchLane]]:
    """GitUp スタイルのマルチレーンレイアウトを計算する。

    Args:
        rows: ``committed_at`` 降順で並んだコミット。
        parents: 子ハッシュをキーとする親ハッシュのリスト（position 順）。
        branches: リポジトリの全ブランチ。

    Returns:
        ノード一覧・エッジ一覧・ブランチレーン一覧のタプル。
    """
    from backend.services.lane_assignment import (
        _assign_lanes,
        _build_hash_to_lane,
        _find_main_hashes,
        build_lane_edges,
        build_lane_nodes,
    )

    if not rows or not branches:
        return [], [], []

    row_set = {r.hash for r in rows}
    hash_to_row = {r.hash: i for i, r in enumerate(rows)}

    main_names = {"main", "master"}
    main_branch = next(
        (b for b in branches if b.name in main_names),
        next((b for b in branches if b.tip_hash == rows[0].hash), branches[0]),
    )

    main_hashes = _find_main_hashes(main_branch.tip_hash, parents, row_set)
    branch_lanes = _assign_lanes(
        branches, main_branch, parents, main_hashes, row_set, hash_to_row, rows
    )
    main_lane = BranchLane(
        name=main_branch.name,
        lane=0,
        tip_hash=main_branch.tip_hash,
        has_unique_commits=True,
        connect_hash=main_branch.tip_hash,
        x=LANE_OFFSET,
    )
    all_lanes = [main_lane] + branch_lanes

    hash_to_lane = _build_hash_to_lane(branch_lanes, parents, main_hashes, row_set)
    nodes = build_lane_nodes(rows, hash_to_lane)
    edges = build_lane_edges(rows, parents, row_set)
    return nodes, edges, all_lanes
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/unit/test_graph_layout.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: コミットする**

```bash
git add backend/services/graph_layout.py tests/unit/test_graph_layout.py
git commit -m "feat: build_multi_lane_layout を実装する"
```

---

## Task 6: ルーターを `build_multi_lane_layout` に切り替える

**Files:**
- Modify: `backend/routers/html.py`

- [ ] **Step 1: `html.py` を更新する**

`backend/routers/html.py` を以下のように変更する:

`import` 部分に `BranchLane` を追加:
```python
from backend.services import graph_layout, sync_service
```
（変更なし。`build_multi_lane_layout` は `graph_layout` モジュール経由で使う）

`graph_page` 内の呼び出しを変更:
```python
    rows = cache_repo.list_recent_commits(session, rid, 50)
    parents = cache_repo.parents_by_child(session, [r.hash for r in rows])
    branches = cache_repo.list_branches(session, rid)
    nodes, edges, branch_lanes = graph_layout.build_multi_lane_layout(
        rows, parents, branches
    )
    context = _build_graph_context(rid, rec, nodes, edges, branch_lanes)
```

`_build_graph_context` を以下に置き換える:
```python
def _build_graph_context(
    rid: str,
    rec: Repository,
    nodes: list,
    edges: list,
    branch_lanes: list,
) -> dict:
    """グラフ画面のテンプレートコンテキストを構築する。

    Args:
        rid: リポジトリ ID。
        rec: リポジトリレコード。
        nodes: レイアウト済みノード一覧。
        edges: エッジ一覧。
        branch_lanes: ブランチレーン一覧。

    Returns:
        Jinja2 テンプレートに渡すコンテキスト辞書。
    """
    from backend.services.graph_layout import LANE_COLORS, ROW_SPACING

    max_lane = max((bl.lane for bl in branch_lanes), default=0)
    svg_width = max(320, max_lane * 70 + 300)
    svg_height = 80.0 + max(len(nodes), 1) * ROW_SPACING
    return {
        "repo_id": rid,
        "repo_name": rec.name,
        "nodes": nodes,
        "edges": edges,
        "branch_lanes": branch_lanes,
        "position_by_hash": {n.commit.hash: n for n in nodes},
        "svg_width": svg_width,
        "svg_height": svg_height,
        "lane_colors": LANE_COLORS,
    }
```

- [ ] **Step 2: 統合テストが通ることを確認する**

```bash
uv run pytest tests/integration/ -v
```

期待: 全テスト PASS

- [ ] **Step 3: コミットする**

```bash
git add backend/routers/html.py
git commit -m "feat: ルーターを build_multi_lane_layout に切り替える"
```

---

## Task 7: `graph.html` テンプレートをマルチレーン対応にする

**Files:**
- Modify: `backend/templates/graph.html`

- [ ] **Step 1: テンプレートを全面書き換えする**

`backend/templates/graph.html` を以下に置き換える:

```jinja2
{% extends "base.html" %}
{% block title %}{{ repo_name }} — グラフ{% endblock %}
{% block body %}
<main class="l--flex" style="min-height: 100vh">
  <section class="-p:20 -ov:auto -bgc:white" aria-label="コミットグラフ"
           style="flex: 2; border-right: 1px solid var(--divider)">
    <header>
      <h1>{{ repo_name }}</h1>
      <p class="-c:text-2 -fz:s">直近 50 コミット</p>
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
        {# ブランチ名ラベル（斜め -40°・下端 Y=95 で下揃え） #}
        {% for bl in branch_lanes %}
          {% set color = lane_colors[bl.lane % 8] %}
          <text
            transform="rotate(-40,{{ bl.x }},95)"
            x="{{ bl.x }}"
            y="95"
            font-size="11"
            fill="{{ color }}"
            font-weight="bold"
          >{{ bl.name }}</text>
        {% endfor %}

        {# 波線：独自コミットなしブランチ（シンボル丸 + 波線） #}
        {% for bl in branch_lanes %}
          {% if not bl.has_unique_commits and bl.connect_hash in position_by_hash %}
            {% set color = lane_colors[bl.lane % 8] %}
            {% set target = position_by_hash[bl.connect_hash] %}
            <line
              x1="{{ bl.x }}" y1="145"
              x2="{{ target.x }}" y2="{{ target.y }}"
              stroke="{{ color }}"
              stroke-width="2"
              stroke-dasharray="5,4"
            />
            <circle cx="{{ bl.x }}" cy="145" r="5" fill="{{ color }}"/>
          {% endif %}
        {% endfor %}

        {# エッジ（コミット間の接続線） #}
        {% for e in edges %}
          {% set c = position_by_hash[e.child_hash] %}
          {% set p = position_by_hash[e.parent_hash] %}
          {% set color = lane_colors[c.lane % 8] %}
          <line
            x1="{{ c.x }}" y1="{{ c.y }}"
            x2="{{ p.x }}" y2="{{ p.y }}"
            stroke="{{ color }}"
            stroke-width="2.5"
          />
        {% endfor %}

        {# コミット円 #}
        {% for node in nodes %}
          {% set color = lane_colors[node.lane % 8] %}
          <g
            class="commit-node"
            hx-get="/repos/{{ repo_id }}/commits/{{ node.commit.hash }}/detail"
            hx-target="#commit-detail"
            hx-swap="innerHTML"
            _="on click remove .selected from .commit-node then add .selected to me"
          >
            <circle cx="{{ node.x }}" cy="{{ node.y }}" r="8" fill="{{ color }}"/>
            <text
              x="{{ node.x + 15 }}"
              y="{{ node.y + 4 }}"
              font-size="12"
              fill="var(--text)"
            >{{ node.commit.message.split('\n')[0] | truncate(40, killwords=True, end='…') }}</text>
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

- [ ] **Step 2: 開発サーバーで動作確認する**

```bash
uv run task dev
```

ブラウザで `http://localhost:8000` を開き、リポジトリを登録してグラフ画面を確認する。

確認事項:
- ブランチ名ラベルが斜めに表示される
- 各ブランチのコミットが色付き円で表示される
- エッジがレーン間を正しく結ぶ

- [ ] **Step 3: コミットする**

```bash
git add backend/templates/graph.html
git commit -m "feat: graph.html をマルチレーン表示に対応させる"
```

---

## Task 8: テストサポートとE2Eテストを追加する

**Files:**
- Modify: `tests/support/git_repo_fixture.py`
- Modify: `tests/e2e/test_graph_smoke.py`

- [ ] **Step 1: マルチブランチ fixture を追加する**

`tests/support/git_repo_fixture.py` の末尾に追加する:

```python
def make_two_branch_repo(path: Path) -> Path:
    """main と feat ブランチを持つリポジトリを作成する。

    Args:
        path: リポジトリのルートディレクトリ。

    Returns:
        作成したリポジトリのパス。
    """
    path.mkdir(parents=True, exist_ok=True)
    repo = pygit2.init_repository(str(path), False)
    sig = pygit2.Signature("テスト", "t@example.com", int(time.time()), 0)

    (path / "a.txt").write_text("a\n", encoding="utf-8")
    repo.index.add("a.txt")
    repo.index.write()
    tree1 = repo.index.write_tree()
    oid1 = repo.create_commit("refs/heads/main", sig, sig, "first", tree1, [])

    repo.create_branch("feat", repo.get(oid1), False)

    (path / "b.txt").write_text("b\n", encoding="utf-8")
    repo.index.add("b.txt")
    repo.index.write()
    tree2 = repo.index.write_tree()
    repo.create_commit("refs/heads/feat", sig, sig, "feat commit", tree2, [oid1])

    (path / "c.txt").write_text("c\n", encoding="utf-8")
    repo.index.add("c.txt")
    repo.index.write()
    tree3 = repo.index.write_tree()
    repo.create_commit("refs/heads/main", sig, sig, "second", tree3, [oid1])

    return path
```

- [ ] **Step 2: E2E テストを追加する**

`tests/e2e/test_graph_smoke.py` の末尾に追加する:

```python
from tests.support.git_repo_fixture import make_two_branch_repo


def test_マルチブランチリポジトリでグラフにコミットノードが表示される(
    page: Page, base_url: str, tmp_path: Path
):
    # Given: main と feat ブランチを持つリポジトリ
    repo_path = make_two_branch_repo(tmp_path / "e2e-multi-repo")

    # When: リポジトリを登録する
    response = page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})

    # Then: グラフに複数のコミットノードが含まれる
    assert response.ok
    body = response.text()
    assert body.count("commit-node") >= 3
```

- [ ] **Step 3: E2E テストを実行する**

```bash
uv run task test:e2e
```

期待: 全 E2E テスト PASS

- [ ] **Step 4: 全テストを実行する**

```bash
uv run task test
```

期待: 全テスト PASS

- [ ] **Step 5: コミットする**

```bash
git add tests/support/git_repo_fixture.py tests/e2e/test_graph_smoke.py
git commit -m "test: マルチブランチ fixture と E2E テストを追加する"
```

---

## 完了チェックリスト

- [ ] `uv run task test` が全 PASS
- [ ] `uv run task lint` がエラーなし
- [ ] `uv run task typecheck` がエラーなし
- [ ] ブラウザで実際のリポジトリのマルチレーングラフが表示される
- [ ] `graph_layout.py` が 150 行以内
- [ ] `lane_assignment.py` が 150 行以内
