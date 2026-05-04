# ブランチ並び順 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** フォークポイントが新しいブランチほどグラフの左レーンに配置されるようにする。

**Architecture:** reach 伝播アルゴリズム（`fork_point.py`）で各ブランチのフォークポイントを計算して SQLite にキャッシュする。`build_layout` はブランチをフォークポイント順にソートしてから `init_branch_maps` に渡す。

**Tech Stack:** Python 3.12+, SQLModel, SQLite, pytest

---

## ファイル一覧

| ファイル | 種別 | 変更内容 |
|---|---|---|
| `docs/graph-algorithm.md` | 修正 | ブランチ並び順ルールを追記 |
| `backend/models.py` | 修正 | `Branch` に `fork_hash`・`fork_committed_at` 追加 |
| `backend/services/fork_point.py` | 新規 | `ForkData`, `compute_fork_data`, `sort_branches_by_fork_data`, `persist_fork_points` |
| `backend/services/grid_builder.py` | 修正 | `build_layout` にソートを追加（line 64） |
| `tests/unit/test_fork_point.py` | 新規 | `compute_fork_data` と `sort_branches_by_fork_data` の単体テスト |
| `tests/unit/test_grid_builder.py` | 修正 | ソート後のレーン割り当てを検証するテストを追加 |
| マイグレーションファイル | 修正 | `branch` テーブルにカラム追加 |

---

## Task 1: docs/graph-algorithm.md にブランチ並び順セクションを追加する

**Files:**
- Modify: `docs/graph-algorithm.md`

- [ ] **Step 1: 「レイアウトアルゴリズム」セクションの直前に並び順セクションを追加する**

`docs/graph-algorithm.md` の line 118（`## レイアウトアルゴリズム` の直前）に挿入する:

```markdown
## ブランチの左右並び順

ブランチをレーンに割り当てる前に、以下のルールで左右順を決定する。

- フォークポイント（分岐元コミット）の `committed_at` が**新しいブランチほど左**（小さいレーン番号）に配置する
- フォークポイントが同一のブランチ間は、専有コミットの最古のもの（bottom_excl）の
  `committed_at` が新しい方を左にする（tie-break）
- フォークポイントが算出できないブランチ（単一ブランチ、またはフォーク元がウィンドウ外）は最右に配置する

フォークポイントは `Branch.fork_committed_at` に UNIX タイムスタンプで保存し、グラフ描画時に読み取る。
計算アルゴリズムは `backend/services/fork_point.py` の `compute_fork_data()` を参照する。

```

- [ ] **Step 2: コミット**

```bash
git add docs/graph-algorithm.md
git commit -m "docs: graph-algorithm.md にブランチ並び順ルールを追記する"
```

---

## Task 2: Branch モデルにカラムを追加してマイグレーションする

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: `Branch` クラスに 2 フィールドを追加する**

`backend/models.py` の `Branch` クラスを以下に変更する（既存フィールドはそのまま残す）:

```python
class Branch(SQLModel, table=True):
    name: str = Field(primary_key=True)
    repo_id: str = Field(primary_key=True, foreign_key="repositories.id")
    tip_hash: str
    is_remote: int = Field(default=0)
    fork_hash: str | None = Field(default=None)          # フォークポイントのコミットハッシュ
    fork_committed_at: int | None = Field(default=None)  # フォークポイントの UNIX タイムスタンプ
```

- [ ] **Step 2: マイグレーションを実行する**

```bash
uv run task migrate
```

Expected: `branch` テーブルに `fork_hash TEXT` と `fork_committed_at INTEGER` カラムが追加される。

- [ ] **Step 3: コミット**

```bash
git add backend/models.py
git commit -m "feat: Branch モデルにフォークポイントカラムを追加する"
```

---

## Task 3: fork_point.py — compute_fork_data の実装（TDD）

**Files:**
- Create: `backend/services/fork_point.py`
- Create: `tests/unit/test_fork_point.py`

- [ ] **Step 1: テストファイルとヘルパーを作成する**

`tests/unit/test_fork_point.py`:

```python
from __future__ import annotations
from backend.models import Branch, Commit
from backend.services.fork_point import ForkData, compute_fork_data


def _c(h: str, at: int) -> Commit:
    return Commit(
        hash=h,
        short_hash=h[:7],
        message="",
        author_name="",
        author_email="",
        committed_at=at,
        repo_id="repo1",
    )


def _b(name: str, tip: str) -> Branch:
    return Branch(name=name, repo_id="repo1", tip_hash=tip)
```

- [ ] **Step 2: 5 つのテストを書く**

```python
def test_単一ブランチはfork_committed_atがNone():
    # --- Arrange ---
    commits = [_c("B", at=20), _c("A", at=10)]
    parents = {"B": ["A"], "A": []}
    branches = [_b("main", tip="B")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    assert result["main"].fork_committed_at is None
    assert result["main"].fork_hash is None


def test_2ブランチ単純分岐でforkが分岐点コミット():
    # --- Arrange ---
    # E(50) - D(30) - C(20) - B(10) - A(5)  main tip=E
    #                  |
    #                  F(25) - G(40)          feature tip=G
    commits = [
        _c("E", at=50), _c("G", at=40), _c("D", at=30),
        _c("F", at=25), _c("C", at=20), _c("B", at=10), _c("A", at=5),
    ]
    parents = {
        "E": ["D"], "G": ["F"], "D": ["C"],
        "F": ["C"], "C": ["B"], "B": ["A"], "A": [],
    }
    branches = [_b("main", tip="E"), _b("feature", tip="G")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    # どちらの分岐元も C（committed_at=20）
    assert result["main"].fork_committed_at == 20
    assert result["main"].fork_hash == "C"
    assert result["feature"].fork_committed_at == 20
    assert result["feature"].fork_hash == "C"
    # bottom_excl: main=D(30), feature=F(25)
    assert result["main"].bottom_committed_at == 30
    assert result["feature"].bottom_committed_at == 25


def test_自分のtipが他のブランチ親の場合はNoneになる():
    # --- Arrange ---
    # main tip=C、feat-2 は C から分岐 → C の reach が {C, E} となり main に専有コミットなし
    # C(30) - B(10) - A(5)  main tip=C
    # |
    # E(45)                 feat-2 tip=E
    commits = [
        _c("E", at=45), _c("C", at=30), _c("D", at=20),
        _c("B", at=10), _c("A", at=5),
    ]
    parents = {
        "E": ["C"], "C": ["B"], "D": ["B"], "B": ["A"], "A": [],
    }
    branches = [_b("main", tip="C"), _b("feat-1", tip="D"), _b("feat-2", tip="E")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    assert result["main"].fork_committed_at is None   # trunk → 最右
    assert result["feat-1"].fork_committed_at == 10   # parent(D) = B(at=10)
    assert result["feat-2"].fork_committed_at == 30   # parent(E) = C(at=30)


def test_同一forkpointはbottom_committed_atが設定される():
    # --- Arrange ---
    # B から feat-A(C,at=20) と feat-B(D,at=15) が分岐
    commits = [_c("C", at=20), _c("D", at=15), _c("B", at=10), _c("A", at=5)]
    parents = {"C": ["B"], "D": ["B"], "B": ["A"], "A": []}
    branches = [_b("feat-A", tip="C"), _b("feat-B", tip="D")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    assert result["feat-A"].fork_committed_at == 10  # parent(C)=B(at=10)
    assert result["feat-B"].fork_committed_at == 10  # parent(D)=B(at=10)
    assert result["feat-A"].bottom_committed_at == 20  # C
    assert result["feat-B"].bottom_committed_at == 15  # D


def test_フォークポイントがウィンドウ外の場合はNone():
    # --- Arrange ---
    # F の親 X はウィンドウ内に存在しない
    commits = [_c("F", at=30), _c("E", at=20)]
    parents = {"F": ["X"], "E": ["X"]}  # X はリストに含まれない
    branches = [_b("main", tip="E"), _b("feature", tip="F")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    # fork_hash は記録されるが committed_at は None（ウィンドウ外）
    assert result["main"].fork_committed_at is None
    assert result["feature"].fork_committed_at is None
```

- [ ] **Step 3: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_fork_point.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.services.fork_point'`

- [ ] **Step 4: `fork_point.py` を実装する**

`backend/services/fork_point.py`:

```python
"""ブランチのフォークポイント計算サービス。"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from backend.models import Branch, Commit


@dataclass
class ForkData:
    """ブランチのフォークポイント情報。"""

    fork_hash: str | None
    fork_committed_at: int | None
    bottom_committed_at: int | None


def compute_fork_data(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
) -> dict[str, ForkData]:
    """各ブランチのフォークポイントを計算する。

    Args:
        commits: トポロジカル順（新→古）のコミットリスト。
        parents: コミットハッシュ → 親ハッシュリストのマップ。
        branches: ブランチリスト。

    Returns:
        ブランチ名 → ForkData のマップ。
    """
    children_map = _build_children_map(parents)
    commit_by_hash = {c.hash: c for c in commits}
    tip_set = {b.tip_hash for b in branches}
    tip_to_name = {b.tip_hash: b.name for b in branches}
    reach = _compute_reach(commits, children_map, tip_set)
    bottom_excl = _find_bottom_excl(commits, reach, tip_to_name)
    return {
        b.name: _derive_fork_data(b, bottom_excl, commit_by_hash, parents)
        for b in branches
    }


def _build_children_map(parents: dict[str, list[str]]) -> dict[str, list[str]]:
    """親 → 子のマップを構築する。"""
    children: dict[str, list[str]] = defaultdict(list)
    for child, parent_list in parents.items():
        for p in parent_list:
            children[p].append(child)
    return dict(children)


def _compute_reach(
    commits: list[Commit],
    children_map: dict[str, list[str]],
    tip_set: set[str],
) -> dict[str, frozenset[str]]:
    """各コミットに到達可能なブランチ tip ハッシュの集合を計算する。"""
    reach: dict[str, frozenset[str]] = {}
    for commit in commits:
        r: set[str] = set()
        for child in children_map.get(commit.hash, []):
            r |= reach.get(child, frozenset())
        if commit.hash in tip_set:
            r.add(commit.hash)
        reach[commit.hash] = frozenset(r)
    return reach


def _find_bottom_excl(
    commits: list[Commit],
    reach: dict[str, frozenset[str]],
    tip_to_name: dict[str, str],
) -> dict[str, str]:
    """各ブランチの最古の専有コミットハッシュを返す。"""
    bottom: dict[str, str] = {}
    for commit in commits:
        r = reach.get(commit.hash, frozenset())
        if len(r) == 1:
            tip = next(iter(r))
            if tip in tip_to_name:
                bottom[tip_to_name[tip]] = commit.hash
    return bottom


def _derive_fork_data(
    branch: Branch,
    bottom_excl: dict[str, str],
    commit_by_hash: dict[str, Commit],
    parents: dict[str, list[str]],
) -> ForkData:
    """bottom_excl からフォークポイントデータを導出する。"""
    bottom_hash = bottom_excl.get(branch.name)
    if bottom_hash is None:
        return ForkData(fork_hash=None, fork_committed_at=None, bottom_committed_at=None)
    bottom_commit = commit_by_hash[bottom_hash]
    parent_list = parents.get(bottom_hash, [])
    if not parent_list:
        return ForkData(
            fork_hash=None, fork_committed_at=None,
            bottom_committed_at=bottom_commit.committed_at,
        )
    fork_hash = parent_list[0]
    fork_commit = commit_by_hash.get(fork_hash)
    if fork_commit is None:
        return ForkData(
            fork_hash=fork_hash, fork_committed_at=None,
            bottom_committed_at=bottom_commit.committed_at,
        )
    return ForkData(
        fork_hash=fork_commit.hash,
        fork_committed_at=fork_commit.committed_at,
        bottom_committed_at=bottom_commit.committed_at,
    )
```

- [ ] **Step 5: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_fork_point.py -v
```

Expected: 5 tests PASS

- [ ] **Step 6: コミット**

```bash
git add backend/services/fork_point.py tests/unit/test_fork_point.py
git commit -m "feat: ブランチのフォークポイント計算を実装する"
```

---

## Task 4: fork_point.py — sort_branches_by_fork_data と persist_fork_points の実装（TDD）

**Files:**
- Modify: `backend/services/fork_point.py`（末尾に追加）
- Modify: `tests/unit/test_fork_point.py`（テスト追加）

- [ ] **Step 1: sort のテストを書く**

`tests/unit/test_fork_point.py` に追記する:

```python
def test_sort_branches_by_fork_data_でnullが右端になる():
    # --- Arrange ---
    from backend.services.fork_point import sort_branches_by_fork_data

    branches = [_b("main", "A"), _b("feature", "B")]
    fork_data = {
        "main": ForkData(fork_hash=None, fork_committed_at=None, bottom_committed_at=10),
        "feature": ForkData(fork_hash="X", fork_committed_at=20, bottom_committed_at=25),
    }

    # --- Act ---
    result = sort_branches_by_fork_data(branches, fork_data)

    # --- Assert ---
    assert result[0].name == "feature"  # fork=20 → 左
    assert result[1].name == "main"     # fork=None → 右


def test_sort_branches_by_fork_data_で同一forkはbottomで順序決定():
    # --- Arrange ---
    from backend.services.fork_point import sort_branches_by_fork_data

    branches = [_b("feat-A", "C"), _b("feat-B", "D")]
    fork_data = {
        "feat-A": ForkData(fork_hash="B", fork_committed_at=10, bottom_committed_at=20),
        "feat-B": ForkData(fork_hash="B", fork_committed_at=10, bottom_committed_at=15),
    }

    # --- Act ---
    result = sort_branches_by_fork_data(branches, fork_data)

    # --- Assert ---
    assert result[0].name == "feat-A"  # bottom=20（新しい）→ 左
    assert result[1].name == "feat-B"  # bottom=15（古い）→ 右
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_fork_point.py::test_sort_branches_by_fork_data_でnullが右端になる tests/unit/test_fork_point.py::test_sort_branches_by_fork_data_で同一forkはbottomで順序決定 -v
```

Expected: `ImportError`（`sort_branches_by_fork_data` 未定義）

- [ ] **Step 3: `sort_branches_by_fork_data` と `persist_fork_points` を `fork_point.py` 末尾に追加する**

```python
def sort_branches_by_fork_data(
    branches: list[Branch],
    fork_data: dict[str, ForkData],
) -> list[Branch]:
    """フォークポイントの新しい順にブランチをソートする。

    Args:
        branches: ソート対象のブランチリスト。
        fork_data: compute_fork_data の返り値。

    Returns:
        フォークポイント降順（新→旧）でソートされたブランチリスト。
        フォークポイントが None のブランチは末尾（最右）に配置される。
    """
    def _key(b: Branch) -> tuple[int, int]:
        data = fork_data.get(b.name)
        if data is None or data.fork_committed_at is None:
            return (1, 0)
        return (-data.fork_committed_at, -(data.bottom_committed_at or 0))

    return sorted(branches, key=_key)


def persist_fork_points(
    session: object,
    branches: list[Branch],
    fork_data: dict[str, ForkData],
) -> None:
    """フォークポイントを DB に保存する。変化がないブランチはスキップする。

    Args:
        session: SQLModel セッション。
        branches: 更新対象のブランチリスト（in-place で更新される）。
        fork_data: compute_fork_data の返り値。
    """
    for branch in branches:
        data = fork_data.get(branch.name)
        if data is None:
            continue
        if (branch.fork_hash, branch.fork_committed_at) == (
            data.fork_hash,
            data.fork_committed_at,
        ):
            continue
        branch.fork_hash = data.fork_hash
        branch.fork_committed_at = data.fork_committed_at
        session.add(branch)  # type: ignore[attr-defined]
    session.commit()  # type: ignore[attr-defined]
```

- [ ] **Step 4: テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_fork_point.py -v
```

Expected: 7 tests PASS

- [ ] **Step 5: コミット**

```bash
git add backend/services/fork_point.py tests/unit/test_fork_point.py
git commit -m "feat: ブランチのフォークポイントソートと DB 保存を実装する"
```

---

## Task 5: grid_builder.py にブランチソートを統合する（TDD）

**Files:**
- Modify: `backend/services/grid_builder.py`
- Modify: `tests/unit/test_grid_builder.py`

- [ ] **Step 1: テストを書く**

`tests/unit/test_grid_builder.py` のインポートブロックに追加する:

```python
# 既存インポートはそのまま。以下を末尾のテストに追加する。
```

ファイル末尾に追記する:

```python
def test_ケース16_フォークが新しいブランチが左レーン():
    # --- Arrange ---
    # main tip=D(50), feat-new tip=F(35, fork=C(30)), feat-old tip=E(15, fork=B(10))
    # 期待: sort後 main(fork=C=30,bottom=D=50) → lane1
    #       feat-new(fork=C=30,bottom=F=35) → lane4
    #       feat-old(fork=B=10) → lane7
    commits = [
        _c("D", [], at=50),  # main tip
        _c("F", [], at=35),  # feat-new tip
        _c("C", [], at=30),  # 共有
        _c("E", [], at=15),  # feat-old tip
        _c("B", [], at=10),  # 共有
        _c("A", [], at=5),   # root
    ]
    parents = _p(
        commits,
        {"D": ["C"], "F": ["C"], "C": ["B"], "E": ["B"], "B": ["A"]},
    )
    branches = [
        _b("main", "D"),
        _b("feat-old", "E"),
        _b("feat-new", "F"),
    ]

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    node_D = next(n for n in layout.nodes if n.hash == "D" and n.kind == "commit")
    node_F = next(n for n in layout.nodes if n.hash == "F" and n.kind == "commit")
    node_E = next(n for n in layout.nodes if n.hash == "E" and n.kind == "commit")
    assert node_D.lane == 1, f"main(D) は lane 1 のはず。実際: {node_D.lane}"
    assert node_F.lane == 4, f"feat-new(F) は lane 4 のはず。実際: {node_F.lane}"
    assert node_E.lane == 7, f"feat-old(E) は lane 7 のはず。実際: {node_E.lane}"


def test_ケース17_フォークNULLのブランチが右端レーン():
    # --- Arrange ---
    # main tip=C(30)、feat tip=E(50)、E の親=C
    # → reach[C] = {C, E}（main の tip C が feat の親コミット）
    # → main に専有コミットなし → fork=None → 右端
    # → feat fork=C(at=30) → 左
    commits = [
        _c("E", [], at=50),   # feat tip, parent=C
        _c("C", [], at=30),   # main tip
        _c("B", [], at=10),
        _c("A", [], at=5),
    ]
    parents = _p(commits, {"E": ["C"], "C": ["B"], "B": ["A"]})
    branches = [_b("main", "C"), _b("feat", "E")]

    # --- Act ---
    layout = build_layout(commits, parents, branches, tags=[])

    # --- Assert ---
    node_E = next(n for n in layout.nodes if n.hash == "E" and n.kind == "commit")
    node_C = next(n for n in layout.nodes if n.hash == "C" and n.kind == "commit")
    assert node_E.lane < node_C.lane, (
        f"feat(E) は main(C) より左レーンのはず。E={node_E.lane}, C={node_C.lane}"
    )
```

- [ ] **Step 2: テストが FAIL することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py::test_ケース16_フォークが新しいブランチが左レーン tests/unit/test_grid_builder.py::test_ケース17_フォークNULLのブランチが右端レーン -v
```

Expected: FAIL（ブランチのソートがまだ行われていない）

- [ ] **Step 3: `grid_builder.py` の `build_layout` を修正する**

`backend/services/grid_builder.py` を以下のように変更する:

インポートに追加（line 10 付近）:
```python
from backend.services.fork_point import compute_fork_data, sort_branches_by_fork_data
```

`build_layout` 関数の先頭（line 64）を以下に置き換える:

```python
def build_layout(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    head_hash: str | None = None,
) -> GridLayout:
    """グリッドレイアウトを計算する。"""
    fork_data = compute_fork_data(commits, parents, branches)
    sorted_branches = sort_branches_by_fork_data(branches, fork_data)
    tip_lane, color_map, tip_color = init_branch_maps(sorted_branches)
    layout = GridLayout()
    sorted_commits = sorted(commits, key=lambda c: -c.committed_at)
    placed = _place_commits(
        sorted_commits,
        parents,
        tip_lane,
        tip_color,
        set(tip_lane.values()),
        layout,
    )
    build_dummy_nodes(layout, sorted_branches, tip_lane, color_map, placed)
    build_edge_graph(layout, parents, placed)
    tag_map = _build_tag_map(tags)
    for label in _build_branch_labels(sorted_branches, tip_lane, color_map, placed, tag_map):
        layout.branch_labels.append(label)
    return layout
```

- [ ] **Step 4: 全テストが PASS することを確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

Expected: 全テスト（既存 15 ケース + 新規 2 ケース）PASS

- [ ] **Step 5: コミット**

```bash
git add backend/services/grid_builder.py tests/unit/test_grid_builder.py
git commit -m "feat: build_layout にブランチフォークポイントソートを統合する"
```

---

## Task 6: ルーターから persist_fork_points を呼び出す

**Files:**
- Modify: `backend/routers/html.py`（または build_grid を呼ぶルーター）

- [ ] **Step 1: ルーターを確認する**

```bash
grep -rn "build_grid\|build_layout" backend/routers/ --include="*.py"
```

`build_grid` を呼び出しているルーターファイルとその行を特定する。

- [ ] **Step 2: DB セッションとブランチのクエリを確認する**

特定したファイルを読み、以下を確認する:
- `Session` をどのように取得しているか
- `branches: list[Branch]` をどのようにクエリしているか
- `commits`, `parents` をどのように取得しているか

- [ ] **Step 3: `persist_fork_points` 呼び出しを追加する**

`build_grid` を呼ぶ直前に以下を追加する（既存の commits, parents, branches 変数を使う）:

```python
from backend.services.fork_point import compute_fork_data, persist_fork_points

fork_data = compute_fork_data(commits, parents, branches)
persist_fork_points(session, branches, fork_data)
```

> `compute_fork_data` は `build_layout` 内でも呼ばれるが、persist のために router 側でも呼ぶ。
> 計算コストは O(n×m) で小さいため二重計算は許容する。

- [ ] **Step 4: 開発サーバーで動作確認する**

```bash
uv run task dev
```

ブラウザでグラフ画面を開き、ブランチが左（新しいフォーク）→ 右（古いフォーク）の順で並んでいることを目視確認する。

- [ ] **Step 5: 全テストが PASS することを確認する**

```bash
uv run pytest tests/unit/ -v
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```bash
git add backend/routers/html.py  # 実際のファイル名に合わせる
git commit -m "feat: ルーターからフォークポイントを DB に保存するようにする"
```
