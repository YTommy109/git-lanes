# グリッドグラフエンジン設計

<!-- derived-from ../../../graph-algorithm.md -->
<!-- derived-from ../../../graph-cases.md -->

## 概要

`docs/graph-algorithm.md` に定義されたグリッド方式レイアウトアルゴリズムを実装する新グラフエンジンを追加する。既存の gitup 模倣エンジン（`graph_builder.py` 等）はそのまま残し、新エンジンをルーターで使用する。

---

## ファイル構成

### 新規ファイル

| ファイル | 責務 | 行数目安 |
| --- | --- | --- |
| `backend/services/grid_models.py` | グリッドエンジン専用データモデル（`GridNode`, `GridEdge`, `GridResult`） | ~80 行 |
| `backend/services/grid_builder.py` | レーン割り当て・ノードタイプ判定・エッジ生成のメインロジック | ~120 行 |
| `backend/services/grid_coords.py` | グリッド座標 → SVG ピクセル変換、`SvgNode`/`SvgEdge` への変換 | ~80 行 |
| `tests/unit/test_grid_builder.py` | 11 ケースの単体テスト（1 関数 = 1 ケース） | ~250 行 |

### 変更ファイル

| ファイル | 変更内容 |
| --- | --- |
| `backend/routers/html.py` | `graph_builder` → `grid_builder` の import 差し替え（1〜2 行） |

既存の `graph_builder*.py` / `graph_coords.py` / `graph_models.py` には変更を加えない。

---

## データモデル（`grid_models.py`）

### `GridNode`

グリッド座標系でのノード情報を保持する。

```python
@dataclass
class GridNode:
    commit_hash: str
    lane: int          # 1, 2, 3, 4, ... （graph-algorithm.md の定義通り）
    row: int           # 0 が最新
    node_type: Literal["commit", "dummy", "joint", "merge", "branch_tip"]
    color: str
```

### `GridEdge`

エッジの接続情報を保持する。

```python
@dataclass
class GridEdge:
    from_lane: int
    from_row: int
    to_lane: int
    to_row: int
    color: str
    dashed: bool       # ダミー/ジョイント経由なら True
```

### `GridResult`

既存の `GraphResult`（`SvgNode`, `SvgEdge`, `SvgBranchHeader`）と同じ型を返す。`graph.html` テンプレートをそのまま利用できる。

---

## アルゴリズム（`grid_builder.py`）

<!-- constrained-by ../../../graph-algorithm.md -->

### フェーズ 1: レーン割り当て

`active_lanes`（各レーンの末尾コミット）を左から走査し、`commit.hash in lane.bottom.parent_hashes` で一致レーンを探す。

- 一致あり → そのレーンに配置し `lane.bottom` を更新
- 一致なし → 新規レーンを追加
  - ブランチ名あり（ブランチレーン）: 未使用の 1, 4, 7, … から最小値
  - ブランチ名なし（中間レーン）: 隣接ブランチレーン間の未使用番号（2, 3, 5, 6, …）

ルートコミット（親なし）を処理したら、そのレーンを `active_lanes` から除去する。

### フェーズ 2: ノードタイプ判定

下記の優先順で判定する。

1. `len(parents) >= 2` → `merge`（塗りつぶしなし円）
2. 複数レーンの始点として参照される → `branch_tip`（塗りつぶしなし円）
3. ブランチ先端が行 0 でない → 行 0 に `dummy`（r=3 の小円）を補完
4. それ以外 → `commit`（塗り潰し円）

### フェーズ 3: エッジ生成

| ケース | 処理 |
| --- | --- |
| 同一レーン内の隣接行 | 縦の実線エッジ |
| 異なるレーン間、1 行以内 | 斜めの実線エッジ |
| 異なるレーン間、複数行またぎ | ジョイントノードを 1 行ずつ中継して分割 |
| ダミー/ジョイント関与 | `dashed=True` の破線エッジ |

---

## 座標変換（`grid_coords.py`）

`graph-algorithm.md` の座標系に従う。

| 計算式 | 値 |
| --- | --- |
| レーン N の cx | `20 + N × 30` px |
| 行 M の cy | `72 + M × 30` px |
| キャンバス幅 | `max(cx) + 50` px |
| キャンバス高さ | `max(cy) + 30` px |

`GridNode` / `GridEdge` を `SvgNode` / `SvgEdge` / `SvgBranchHeader` に変換し `GridResult` として返す。

---

## テスト設計（`tests/unit/test_grid_builder.py`）

### 方針

- 1 関数 = 1 ケース（`graph-cases.md` のケース番号と対応）
- `pytest -k "ケース5"` で単一ケースのみ実行可能
- `(lane, row)` と `node_type` でアサート（ピクセル座標には依存しない）
- エッジは `(from_hash, to_hash, dashed)` でアサート

### テストヘルパー

```python
def make_commit(hash: str, parents: list[str]) -> Commit: ...
def make_branch(name: str, tip: str) -> Branch: ...

# ノードをコミットハッシュで引いて lane/row/node_type を検証する
def assert_node(result, hash: str, lane: int, row: int, node_type: str) -> None: ...

# 通常のエッジ（コミット間）: コミットハッシュで指定
def assert_edge(result, from_hash: str, to_hash: str, dashed: bool) -> None: ...

# ジョイントノード/ダミー経由のエッジ: グリッド座標で指定
# ジョイントノードにはコミットハッシュが存在しないため座標指定が必要
def assert_edge_coords(
    result,
    from_lane: int, from_row: int,
    to_lane: int, to_row: int,
    dashed: bool,
) -> None: ...
```

ジョイントノードが関与するケース（ケース 6, 11）では、まず `assert_node` でジョイントノードの `(lane, row)` を確認し、次に `assert_edge_coords` で前後のエッジセグメントを個別にアサートする。

### テスト一覧

| テスト関数名 | 検証の焦点 |
| --- | --- |
| `test_ケース1_コミット1つ` | 単一ノード・レーン 1 |
| `test_ケース2_直線接続` | 縦エッジ |
| `test_ケース3_同じコミットを指す2ブランチ` | ブランチ名ラベル共存 |
| `test_ケース4_2ブランチが同じ親を持つ` | 斜めエッジ |
| `test_ケース5_developがmainの途中から分岐` | ダミーノード + 破線 |
| `test_ケース6_developが古いコミットを指す` | ジョイントノード経由 |
| `test_ケース7_developがmainより新しい` | main 側にダミーノード |
| `test_ケース8_マージ済みブランチ名削除済み` | 中間レーン（レーン 2） |
| `test_ケース9_マージ済み削除ブランチ複数コミット` | 中間レーン + 複数縦エッジ |
| `test_ケース10_削除ブランチとアクティブブランチ混在` | 混在パターン |
| `test_ケース11_2ブランチをマージ後にどちらも削除` | ジョイントノード + 複数削除済み |

### テスト関数の例（ケース 4）

```python
def test_ケース4_2ブランチが同じ親を持つ():
    # --- Arrange ---
    commits = [
        make_commit("a", parents=["c"]),  # main 先端
        make_commit("b", parents=["c"]),  # develop 先端
        make_commit("c", parents=[]),     # 共通の親
    ]
    branches = [make_branch("main", "a"), make_branch("develop", "b")]

    # --- Act ---
    result = build_grid(commits, parents_map(commits), branches, tags=[])

    # --- Assert ---
    assert_node(result, "a", lane=1, row=0, node_type="commit")
    assert_node(result, "b", lane=4, row=0, node_type="commit")
    assert_node(result, "c", lane=1, row=1, node_type="commit")
    assert_edge(result, from_hash="a", to_hash="c", dashed=False)
    assert_edge(result, from_hash="b", to_hash="c", dashed=False)
```

---

## ルーター変更（`html.py`）

```python
# 変更前
from backend.services import graph_builder
result = graph_builder.build_graph(rows, parents, branches, tags, rec.cached_head)

# 変更後
from backend.services import grid_builder
result = grid_builder.build_grid(rows, parents, branches, tags, rec.cached_head)
```

`GridResult` は `GraphResult` と同じフィールドを持つため、テンプレートへ渡す `context` 辞書の変更は不要。
