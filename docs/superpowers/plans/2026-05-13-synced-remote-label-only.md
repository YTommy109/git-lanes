# 同期済みリモートブランチのラベルのみ表示 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 同期済みリモートブランチ（tip が任意ローカルと一致）を独自レーン・線なしで「ラベルのみ」として扱い、`show_remote` トグル時の色変化を解消する。

**Architecture:** `branch_filter.py` に `categorize_branches` を追加してブランチを 3 分類する。`grid_builder_helpers.init_branch_maps` に `label_only_branches` パラメータを追加して color_idx を消費しないよう制御する。`_build_branch_labels` でラベルのみブランチを既存レーンに追記する。`graph_service` で `categorize_branches` を呼び、`show_remote` に応じて `label_only` を切り替える。

**Tech Stack:** Python 3.12 / FastAPI / pytest / unittest.mock

---

### Task 1: branch_filter.py に BranchCategories と categorize_branches を TDD で追加

**Files:**
- Modify: `backend/services/branch_filter.py`
- Modify: `tests/unit/test_branch_filter.py`

- [ ] **Step 1: テストを追記して失敗させる**

`tests/unit/test_branch_filter.py` の末尾に以下を追加する。

```python
from backend.services.branch_filter import BranchCategories, categorize_branches


def test_categorize_branches_ローカルブランチのみの場合はlocalに全て入る():
    # --- Arrange ---
    branches = [
        Branch(name="main", repo_id="r", tip_hash="aaa", is_remote=0),
        Branch(name="feat", repo_id="r", tip_hash="bbb", is_remote=0),
    ]

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert len(cats.local) == 2
    assert cats.synced_remotes == []
    assert cats.diverged_remotes == []


def test_categorize_branches_tipが一致するリモートがsynced_remotesに入る():
    # --- Arrange ---
    branches = [
        Branch(name="main", repo_id="r", tip_hash="aaa", is_remote=0),
        Branch(name="origin/main", repo_id="r", tip_hash="aaa", is_remote=1),
    ]

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert len(cats.synced_remotes) == 1
    assert cats.synced_remotes[0].name == "origin/main"
    assert cats.diverged_remotes == []


def test_categorize_branches_名前が違ってもtipが一致すればsynced_remotesに入る():
    # origin/HEAD のように名前が異なるケースでも tip 一致で分類される
    # --- Arrange ---
    branches = [
        Branch(name="main", repo_id="r", tip_hash="aaa", is_remote=0),
        Branch(name="origin/HEAD", repo_id="r", tip_hash="aaa", is_remote=1),
    ]

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert len(cats.synced_remotes) == 1
    assert cats.synced_remotes[0].name == "origin/HEAD"


def test_categorize_branches_tipが異なるリモートがdiverged_remotesに入る():
    # --- Arrange ---
    branches = [
        Branch(name="main", repo_id="r", tip_hash="aaa", is_remote=0),
        Branch(name="origin/main", repo_id="r", tip_hash="bbb", is_remote=1),
    ]

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert cats.synced_remotes == []
    assert len(cats.diverged_remotes) == 1
    assert cats.diverged_remotes[0].name == "origin/main"


def test_categorize_branches_空リストは空カテゴリを返す():
    # --- Arrange ---
    branches: list[Branch] = []

    # --- Act ---
    cats = categorize_branches(branches)

    # --- Assert ---
    assert cats.local == []
    assert cats.synced_remotes == []
    assert cats.diverged_remotes == []
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```bash
uv run pytest tests/unit/test_branch_filter.py -k "categorize" -v
```

期待: `ImportError: cannot import name 'BranchCategories'` 相当のエラーで FAIL。

- [ ] **Step 3: branch_filter.py に BranchCategories と categorize_branches を実装する**

`backend/services/branch_filter.py` の先頭に以下を追加する（既存の `filter_synced_remote_branches` は残す）。

```python
"""リモートトラッキングブランチのフィルタリング。"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.models import Branch


@dataclass
class BranchCategories:
    """ブランチ分類の結果。"""

    local: list[Branch] = field(default_factory=list)
    synced_remotes: list[Branch] = field(default_factory=list)
    diverged_remotes: list[Branch] = field(default_factory=list)


def categorize_branches(branches: list[Branch]) -> BranchCategories:
    """ブランチをローカル・同期済みリモート・乖離リモートに分類する。

    同期済みリモートの判定は tip_hash で行う（名前は問わない）。
    これにより origin/HEAD のような特殊なリモートも正しく分類できる。

    Args:
        branches: ローカル・リモート混在のブランチリスト。

    Returns:
        分類済み BranchCategories。
    """
    local = [b for b in branches if b.is_remote == 0]
    local_tips = {b.tip_hash for b in local}
    cats = BranchCategories(local=local)
    for b in branches:
        if b.is_remote == 0:
            continue
        if b.tip_hash in local_tips:
            cats.synced_remotes.append(b)
        else:
            cats.diverged_remotes.append(b)
    return cats


def filter_synced_remote_branches(branches: list[Branch]) -> list[Branch]:
    # ... 既存の実装はそのまま残す
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```bash
uv run pytest tests/unit/test_branch_filter.py -v
```

期待: すべて PASS（既存テストも含む）。

- [ ] **Step 5: コミットする**

```bash
git add backend/services/branch_filter.py tests/unit/test_branch_filter.py
git commit -m "feat: branch_filter に categorize_branches を追加する"
```

---

### Task 2: grid_builder_helpers.py の init_branch_maps に label_only_branches を TDD で追加

**Files:**
- Modify: `backend/services/grid_builder_helpers.py`
- Create: `tests/unit/test_init_branch_maps.py`

- [ ] **Step 1: テストファイルを作成して失敗させる**

`tests/unit/test_init_branch_maps.py` を以下の内容で作成する。

```python
"""init_branch_maps の label_only_branches パラメータのテスト。"""

from __future__ import annotations

from backend.models import Branch
from backend.services.grid_builder_helpers import init_branch_maps
from backend.services.grid_models import GRID_COLORS


def _local(name: str, tip: str) -> Branch:
    return Branch(name=name, repo_id="r", tip_hash=tip, is_remote=0)


def _remote(name: str, tip: str) -> Branch:
    return Branch(name=name, repo_id="r", tip_hash=tip, is_remote=1)


def test_label_only_branchesはcolor_idxを消費しない():
    # --- Arrange ---
    # label_only が色インデックスに影響しなければ feat は 2番目の色（GRID_COLORS[1]）になる
    main = _local("main", "aaa")
    feat = _local("feat", "bbb")
    origin_main = _remote("origin/main", "aaa")  # main と同じ tip → label_only

    # --- Act ---
    _, color_map, _ = init_branch_maps([main, feat], label_only_branches=[origin_main])

    # --- Assert ---
    assert color_map["main"] == GRID_COLORS[0]
    assert color_map["feat"] == GRID_COLORS[1]  # label_only の影響で GRID_COLORS[2] にならない
    assert color_map["origin/main"] == GRID_COLORS[0]  # main の色を借用


def test_label_only_branchesは既存レーンの色を借用する():
    # --- Arrange ---
    main = _local("main", "aaa")
    origin_main = _remote("origin/main", "aaa")

    # --- Act ---
    _, color_map, _ = init_branch_maps([main], label_only_branches=[origin_main])

    # --- Assert ---
    assert color_map["origin/main"] == color_map["main"]


def test_label_only_branchesがNoneの場合は既存の動作と同じ():
    # --- Arrange ---
    main = _local("main", "aaa")
    feat = _local("feat", "bbb")

    # --- Act ---
    _, color_map_with, _ = init_branch_maps([main, feat], label_only_branches=None)
    _, color_map_without, _ = init_branch_maps([main, feat])

    # --- Assert ---
    assert color_map_with == color_map_without


def test_label_only_branchesのtipがtip_laneにない場合はcolor_mapに追加しない():
    # tip が tip_lane に存在しない label_only は静かに無視される
    # --- Arrange ---
    main = _local("main", "aaa")
    orphan = _remote("origin/orphan", "zzz")  # どのローカルとも一致しない

    # --- Act ---
    _, color_map, _ = init_branch_maps([main], label_only_branches=[orphan])

    # --- Assert ---
    assert "origin/orphan" not in color_map
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```bash
uv run pytest tests/unit/test_init_branch_maps.py -v
```

期待: `TypeError: init_branch_maps() got an unexpected keyword argument 'label_only_branches'` で FAIL。

- [ ] **Step 3: init_branch_maps に label_only_branches パラメータを実装する**

`backend/services/grid_builder_helpers.py` の `init_branch_maps` を以下に置き換える。

```python
def init_branch_maps(
    branches: list[Branch],
    label_only_branches: list[Branch] | None = None,
) -> tuple[dict[str, int], dict[str, str], dict[str, str]]:
    """ブランチのレーン・色マップを初期化する。

    Args:
        branches: ブランチのリスト。リスト順にレーン番号を割り当てる。
        label_only_branches: レーンを消費せずラベルのみ表示するブランチ。
            color_idx を消費せず、対応する tip のブランチの色を借用する。

    Returns:
        (tip_lane, color_map, tip_color) のタプル。
    """
    branch_lane: dict[str, int] = {}
    tip_lane: dict[str, int] = {}
    color_map: dict[str, str] = {}
    lane_num = 1
    color_idx = 0
    for b in branches:
        if b.name not in branch_lane:
            if b.tip_hash in tip_lane:
                # 同じ tip を持つブランチはレーンを共用し、lane_num を消費しない
                branch_lane[b.name] = tip_lane[b.tip_hash]
            else:
                branch_lane[b.name] = lane_num
                lane_num += 3
            color_map[b.name] = GRID_COLORS[color_idx % len(GRID_COLORS)]
            color_idx += 1
        if b.tip_hash not in tip_lane:
            tip_lane[b.tip_hash] = branch_lane[b.name]
    tip_color: dict[str, str] = {b.tip_hash: color_map[b.name] for b in branches}
    # label_only_branches: color_idx を消費せず既存 tip_color から色を借用する
    for b in (label_only_branches or []):
        if b.name not in color_map and b.tip_hash in tip_color:
            color_map[b.name] = tip_color[b.tip_hash]
    return tip_lane, color_map, tip_color
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```bash
uv run pytest tests/unit/test_init_branch_maps.py -v
```

期待: 4 テストすべて PASS。

- [ ] **Step 5: 既存テストが壊れていないことを確認する**

```bash
uv run pytest tests/unit/ -v
```

期待: すべて PASS。

- [ ] **Step 6: コミットする**

```bash
git add backend/services/grid_builder_helpers.py tests/unit/test_init_branch_maps.py
git commit -m "feat: init_branch_maps に label_only_branches パラメータを追加する"
```

---

### Task 3: _build_branch_labels / build_layout / build_grid に label_only_branches を TDD で追加

**Files:**
- Modify: `backend/services/grid_builder_layout.py`
- Modify: `backend/services/grid_builder.py`
- Modify: `tests/unit/test_grid_builder.py`

- [ ] **Step 1: テストを追記して失敗させる**

`tests/unit/test_grid_builder.py` の末尾に以下を追加する。

```python
def test_label_only_branchesのラベルが既存レーンに追加される():
    # --- Arrange ---
    # コミット A を tip とするローカル main と、同じ tip の origin/main（label_only）
    commit_a = _c("aaaaaaa", [])
    commits = [commit_a]
    parents = _p(commits, {})
    main = Branch(name="main", repo_id=_REPO, tip_hash="aaaaaaa", is_remote=0)
    origin_main = Branch(name="origin/main", repo_id=_REPO, tip_hash="aaaaaaa", is_remote=1)

    # --- Act ---
    layout = build_layout(
        commits, parents, [main], [], label_only_branches=[origin_main]
    )

    # --- Assert ---
    assert len(layout.branch_labels) == 1
    label = layout.branch_labels[0]
    assert "main" in label.names
    assert "origin/main" in label.names


def test_label_only_branchesがないときのbranch_labelsは変わらない():
    # --- Arrange ---
    commit_a = _c("bbbbbbb", [])
    commits = [commit_a]
    parents = _p(commits, {})
    main = Branch(name="main", repo_id=_REPO, tip_hash="bbbbbbb", is_remote=0)

    # --- Act ---
    layout_with = build_layout(commits, parents, [main], [], label_only_branches=None)
    layout_without = build_layout(commits, parents, [main], [])

    # --- Assert ---
    assert layout_with.branch_labels == layout_without.branch_labels
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -k "label_only" -v
```

期待: `TypeError: build_layout() got an unexpected keyword argument 'label_only_branches'` で FAIL。

- [ ] **Step 3: _build_branch_labels に label_only_branches を実装する**

`backend/services/grid_builder_layout.py` の `_build_branch_labels` を以下に置き換える。

```python
def _build_branch_labels(
    branches: list[Branch],
    tip_lane: dict[str, int],
    color_map: dict[str, str],
    placed: dict[str, GridNode],
    tag_map: dict[str, list[str]],
    label_only_branches: list[Branch] | None = None,
) -> list[GridBranchLabel]:
    """ブランチラベルリストを構築する。"""
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
    # label_only_branches: 独自レーンを持たず既存レーンにラベルのみ追記する
    for b in (label_only_branches or []):
        tip_h = b.tip_hash
        if tip_h in placed and placed[tip_h].row == 0:
            target_lane = placed[tip_h].lane
        else:
            target_lane = tip_lane.get(tip_h)
        if target_lane is None:
            continue
        lane_to_names.setdefault(target_lane, []).append(b.name)
    return [
        GridBranchLabel(lane=ln, names=names, color=lane_to_color[ln])
        for ln, names in lane_to_names.items()
    ]
```

- [ ] **Step 4: build_layout に label_only_branches を追加する**

`backend/services/grid_builder_layout.py` は変更済み。次に `backend/services/grid_builder.py` の `build_layout` を以下に置き換える。

```python
def build_layout(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    fork_data: dict[str, ForkData] | None = None,
    label_only_branches: list[Branch] | None = None,
) -> GridLayout:
    """グリッドレイアウトを計算する。"""
    if fork_data is None:
        fork_data = compute_fork_data(commits, parents, branches)
    sorted_branches = sort_branches_by_fork_data(branches, fork_data)
    tip_lane, color_map, tip_color = init_branch_maps(sorted_branches, label_only_branches)
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
    for label in _build_branch_labels(
        sorted_branches, tip_lane, color_map, placed, tag_map, label_only_branches
    ):
        layout.branch_labels.append(label)
    return layout
```

- [ ] **Step 5: build_grid に label_only_branches を追加する**

`backend/services/grid_builder.py` の `build_grid` を以下に置き換える。

```python
def build_grid(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
    tags: list[Tag],
    fork_data: dict[str, ForkData] | None = None,
    label_only_branches: list[Branch] | None = None,
) -> GraphResult:
    """グリッドエンジンでグラフを構築して GraphResult を返す。

    Args:
        commits: コミットのリスト（新しい順）。
        parents: コミットハッシュ → 親ハッシュリスト のマップ。
        branches: ブランチのリスト。
        tags: タグのリスト。
        label_only_branches: レーンを消費せずラベルのみ表示するブランチ。

    Returns:
        SVG テンプレートへ渡す GraphResult。
    """
    from backend.services.grid_coords import to_svg

    tag_map = _build_tag_map(tags)
    layout = build_layout(commits, parents, branches, tags, fork_data, label_only_branches)
    return to_svg(layout, commits, parents, tag_map)
```

- [ ] **Step 6: テストを実行して PASS を確認する**

```bash
uv run pytest tests/unit/test_grid_builder.py -v
```

期待: すべて PASS（既存テスト含む）。

- [ ] **Step 7: コミットする**

```bash
git add backend/services/grid_builder_layout.py backend/services/grid_builder.py tests/unit/test_grid_builder.py
git commit -m "feat: グリッドビルダーに label_only_branches サポートを追加する"
```

---

### Task 4: graph_service.py を categorize_branches に切り替え、既存テストを更新する

**Files:**
- Modify: `backend/services/graph_service.py`
- Modify: `tests/unit/test_graph_service_filter.py`

- [ ] **Step 1: test_graph_service_filter.py に新テストを追記して失敗させる**

`tests/unit/test_graph_service_filter.py` に以下を追加する。

```python
@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags", return_value=[])
@patch("backend.services.graph_service.branch_repo.list_branches")
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_show_remote_trueのとき同期済みリモートがlabel_only_branchesに渡される(
    mock_sync,
    mock_commits,
    mock_parents,
    mock_list_branches,
    mock_list_tags,
    mock_fork_data,
    mock_persist,
    mock_build,
):
    # --- Arrange ---
    # origin/main は main と同じ tip → synced_remote → label_only に渡るはず
    local_main = Branch(name="main", repo_id="r1", tip_hash="aaa", is_remote=0)
    synced_remote = Branch(name="origin/main", repo_id="r1", tip_hash="aaa", is_remote=1)
    mock_list_branches.return_value = [local_main, synced_remote]
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path", show_remote=True)

    # --- Assert ---
    # branches (位置引数 [2]) にはローカルのみ
    branches_arg = mock_build.call_args[0][2]
    assert all(b.is_remote == 0 for b in branches_arg)
    # label_only_branches (キーワード引数) に synced_remote が入る
    label_only_arg = mock_build.call_args.kwargs["label_only_branches"]
    assert len(label_only_arg) == 1
    assert label_only_arg[0].name == "origin/main"


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags", return_value=[])
@patch("backend.services.graph_service.branch_repo.list_branches")
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_show_remote_falseのとき同期済みリモートのlabel_only_branchesが空になる(
    mock_sync,
    mock_commits,
    mock_parents,
    mock_list_branches,
    mock_list_tags,
    mock_fork_data,
    mock_persist,
    mock_build,
):
    # --- Arrange ---
    local_main = Branch(name="main", repo_id="r1", tip_hash="aaa", is_remote=0)
    synced_remote = Branch(name="origin/main", repo_id="r1", tip_hash="aaa", is_remote=1)
    mock_list_branches.return_value = [local_main, synced_remote]
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path", show_remote=False)

    # --- Assert ---
    label_only_arg = mock_build.call_args.kwargs["label_only_branches"]
    assert label_only_arg == []
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```bash
uv run pytest tests/unit/test_graph_service_filter.py -k "label_only" -v
```

期待: `KeyError: 'label_only_branches'` または assertion error で FAIL。

- [ ] **Step 3: graph_service.py を categorize_branches を使うように書き換える**

`backend/services/graph_service.py` を以下に置き換える（`filter_synced_remote_branches` の import を `categorize_branches` に変更）。

```python
"""グラフデータの同期・構築サービス。"""

from __future__ import annotations

import logging

import pygit2
from sqlmodel import Session

from backend.exceptions import GitOpenError
from backend.repositories import branch_repo, commit_repo, tag_repo
from backend.services import grid_builder, sync_service
from backend.services.branch_filter import categorize_branches
from backend.services.fork_point import compute_fork_data, persist_fork_points
from backend.services.graph_models import GraphResult

_logger = logging.getLogger(__name__)


def sync_and_build(
    session: Session,
    repo_id: str,
    repo_path: str,
    show_remote: bool = True,
    show_tags: bool = True,
) -> GraphResult:
    """リポジトリを同期してグラフデータを構築する。

    Args:
        session: DB セッション。
        repo_id: リポジトリ ID。
        repo_path: Git 作業コピーのパス。
        show_remote: False のときリモートブランチを全除外する。
        show_tags: False のときタグラベルを表示しない。

    Returns:
        SVG テンプレートへ渡す GraphResult。

    Raises:
        GitOpenError: Git リポジトリを開けない場合。
    """
    try:
        sync_service.sync_repository(session, repo_id, repo_path)
    except pygit2.GitError as exc:
        raise GitOpenError from exc
    rows = commit_repo.list_all_commits(session, repo_id)
    parents = commit_repo.parents_by_child(session, [r.hash for r in rows])
    cats = categorize_branches(branch_repo.list_branches(session, repo_id))
    label_only = cats.synced_remotes if show_remote else []
    branches = cats.local + (cats.diverged_remotes if show_remote else [])
    tags = tag_repo.list_tags(session, repo_id) if show_tags else []
    _logger.debug(
        "グラフ描画: repo_id=%s commits=%d branches=%d", repo_id, len(rows), len(branches)
    )
    fork_data = compute_fork_data(rows, parents, branches)
    persist_fork_points(session, branches, fork_data)
    return grid_builder.build_grid(
        rows, parents, branches, tags, fork_data, label_only_branches=label_only
    )
```

- [ ] **Step 4: 既存の test_graph_service_filter.py のコメントを更新する**

`_remote` ヘルパーのコメントが古くなっているので更新する。

```python
def _remote(name: str, tip: str = "bbb") -> Branch:
    # tip をローカルと意図的に変えて diverged_remote として扱われるようにする
    return Branch(name=name, repo_id="r1", tip_hash=tip, is_remote=1)
```

- [ ] **Step 5: テストをすべて実行して PASS を確認する**

```bash
uv run pytest tests/unit/ -v
```

期待: すべて PASS。

- [ ] **Step 6: lint と型チェックを実行する**

```bash
uv run task lint && uv run task typecheck
```

期待: エラーなし。

- [ ] **Step 7: コミットする**

```bash
git add backend/services/graph_service.py tests/unit/test_graph_service_filter.py
git commit -m "feat: graph_service を categorize_branches に切り替えて色安定化を実現する"
```
