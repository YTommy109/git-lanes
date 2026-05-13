# 同期済みリモートブランチのラベルのみ表示 設計仕様

<!-- derived-from ./docs/specification.md -->
<!-- derived-from ./docs/superpowers/specs/2026-05-13-remote-tag-toggle-design.md -->

## 概要

リモートブランチの表示トグルを切り替えると、ローカルブランチの線の色が変わる問題を修正する。
原因は「同期済みリモートブランチが `color_idx` を消費してしまうこと」にある。

同期済みリモートブランチ（tip が任意のローカルブランチと一致するリモート）を、独自レーン・線なしで「ラベルのみ」として扱うことで色の安定性を確保する。

## 問題の詳細

`init_branch_maps` 内で、同じ tip を持つブランチは `lane_num` を消費しないが `color_idx` は常にインクリメントされる。
この結果、`show_remote` トグルでリモートブランチ数が変わると、ローカルブランチの色インデックスがずれる。

また、`filter_synced_remote_branches` は「同名のローカルブランチと tip が一致するリモート」しか除外しないため、`origin/HEAD` のような名前が異なるケースが除外されず問題を引き起こす。

## 決定事項

| 項目 | 決定内容 |
|---|---|
| 分類単位 | tip_hash が任意ローカルブランチと一致するか否か（名前は問わない） |
| synced_remotes の扱い | ラベルのみ（独自レーン・線なし）。`color_idx` を消費しない |
| diverged_remotes の扱い | 独自レーン・線あり（現状維持） |
| show_remote=ON | local + diverged のレーン + synced のラベル |
| show_remote=OFF | local のレーンのみ。リモートラベルなし |

## アーキテクチャ

```
categorize_branches(all_branches)
  → local_branches      : is_remote=0
  → synced_remotes      : is_remote=1 かつ tip が任意 local の tip と一致
  → diverged_remotes    : is_remote=1 かつ tip がどの local とも一致しない

graph_service.sync_and_build(show_remote=True):
  branches     = local + diverged_remotes  → 独自レーン・色
  label_only   = synced_remotes            → 既存レーンにラベルのみ追加

graph_service.sync_and_build(show_remote=False):
  branches     = local のみ
  label_only   = []
```

## 変更ファイル

### `backend/services/branch_filter.py`

`filter_synced_remote_branches` を残しつつ `categorize_branches` を追加する。

```python
from dataclasses import dataclass, field

@dataclass
class BranchCategories:
    local: list[Branch] = field(default_factory=list)
    synced_remotes: list[Branch] = field(default_factory=list)
    diverged_remotes: list[Branch] = field(default_factory=list)

def categorize_branches(branches: list[Branch]) -> BranchCategories:
    """ブランチをローカル・同期済みリモート・乖離リモートに分類する。

    同期済みリモートの判定は名前ではなく tip_hash で行う。
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
```

### `backend/services/graph_service.py`

`filter_synced_remote_branches` の呼び出しを `categorize_branches` に置き換える。

```python
from backend.services.branch_filter import categorize_branches

def sync_and_build(
    session: Session,
    repo_id: str,
    repo_path: str,
    show_remote: bool = True,
    show_tags: bool = True,
) -> GraphResult:
    ...
    cats = categorize_branches(branch_repo.list_branches(session, repo_id))
    label_only = cats.synced_remotes if show_remote else []
    branches = cats.local + (cats.diverged_remotes if show_remote else [])
    tags = tag_repo.list_tags(session, repo_id) if show_tags else []
    ...
    return grid_builder.build_grid(rows, parents, branches, tags, fork_data,
                                   label_only_branches=label_only)
```

### `backend/services/grid_builder_helpers.py`

`init_branch_maps` に `label_only_branches` パラメータを追加する。

`label_only_branches` の各ブランチは:
- `tip_lane` に既に登録済みの tip を使って `color_map` に同じ色で登録する
- `lane_num` も `color_idx` も消費しない

```python
def init_branch_maps(
    branches: list[Branch],
    label_only_branches: list[Branch] | None = None,
) -> tuple[dict[str, int], dict[str, str], dict[str, str]]:
    # 既存の branches 処理（変更なし）
    ...
    # label_only_branches: 色をローカルブランチから借用
    for b in (label_only_branches or []):
        if b.name not in color_map and b.tip_hash in tip_lane:
            # 同じ tip のローカルブランチの色を使用
            local_color = tip_color.get(b.tip_hash, GRID_COLORS[0])
            color_map[b.name] = local_color
    return tip_lane, color_map, tip_color
```

### `backend/services/grid_builder_layout.py`

`_build_branch_labels` に `label_only_branches` パラメータを追加する。

```python
def _build_branch_labels(
    branches: list[Branch],
    tip_lane: dict[str, int],
    color_map: dict[str, str],
    placed: dict[str, GridNode],
    tag_map: dict[str, list[str]],
    label_only_branches: list[Branch] | None = None,
) -> list[GridBranchLabel]:
```

既存の `lane_to_names` 構築ループの後に、`label_only_branches` の名前をその tip_hash が属するレーンに追記する。

```python
for b in (label_only_branches or []):
    tip_h = b.tip_hash
    if tip_h in placed and placed[tip_h].row == 0:
        target_lane = placed[tip_h].lane
    else:
        target_lane = tip_lane.get(tip_h)
    if target_lane is None:
        continue
    lane_to_names.setdefault(target_lane, []).append(b.name)
```

### `backend/services/grid_builder.py`

`build_layout` と `build_grid` に `label_only_branches` パラメータを追加して内部に伝播する。

```python
def build_grid(
    commits, parents, branches, tags,
    fork_data=None,
    label_only_branches: list[Branch] | None = None,
) -> GraphResult:
```

## テスト方針

### `tests/unit/test_branch_filter.py` — `categorize_branches` のテスト追加

- `is_remote=0` がすべて `local` に入ること
- `tip` が一致するリモートが `synced_remotes` に入ること（名前が異なっても、例: `origin/HEAD`）
- `tip` が一致しないリモートが `diverged_remotes` に入ること

### `tests/unit/test_graph_service_filter.py` — 既存テスト更新

- `show_remote=False` でリモートが全除外されること（`label_only` も空）
- `show_remote=True` で synced_remotes が `label_only_branches` として渡されること
- デフォルトで `show_remote=True` であること

### `tests/unit/test_grid_builder_helpers.py` — `init_branch_maps` のテスト追加

- `label_only_branches` が `color_idx` を消費しないこと（後続ブランチの色が変わらない）
- `label_only_branches` が既存レーンの色を借用すること

## 対象外

- diverged リモートの表示スタイル変更
- リモートラベルの位置や見た目の変更（バッジ形式は現状維持）
