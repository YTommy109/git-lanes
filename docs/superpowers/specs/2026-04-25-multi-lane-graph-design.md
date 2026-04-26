# マルチレーングラフ設計書

## 概要

GitUp スタイルのマルチレーングラフ表示を実装する。
各ブランチが独立した縦レーンを持ち、ブランチ名が斜めラベルとして上部に並ぶ。
接続線の交差を最小化するため、main との接続点が上（新しい）ほど内側レーンに配置する。

---

## ビジュアル仕様

### レイアウト規則

- ブランチ名ラベル: 斜め -40° 表示、下端アンカー Y=95 で下揃え
- 最初のコミット行: Y=145（ラベルとの差 20px）
- 行間隔: 60px 固定（コミットのないレーンはスキップするが間隔は変えない）
- レーン間隔: 70px（X = lane × 70 + 36）

### コミットの表示

| 種別 | 表示 |
| --- | --- |
| 通常コミット | 白塗り円（r=7）、レーン色でストローク |
| 先端コミット（tip） | レーン色塗り円（r=8） |
| HEAD | 赤背景の「HEAD」ラベル矩形 |
| マージコミット | 白塗り円（r=9）、マージ元レーン色でストローク |

### ブランチの表示

| 種別 | 表示 |
| --- | --- |
| 独自コミットあり | 実線の縦レーン + 末尾から main への斜め実線 |
| 独自コミットなし（ブランチ作成のみ） | 上揃え行にシンボル小丸（r=5）+ 指定コミットへ波線（stroke-dasharray="5,4"）|

### カラーパレット（8色サイクル）

```python
LANE_COLORS = [
    "#e05555",  # 0: main（赤）
    "#e67e22",  # 1: オレンジ
    "#2ecc71",  # 2: 緑
    "#3498db",  # 3: 青
    "#9b59b6",  # 4: 紫
    "#1abc9c",  # 5: ティール
    "#f1c40f",  # 6: 黄
    "#e91e63",  # 7: ピンク
]
```

---

## データ構造

### 変更なし

既存の `CommitParent.position`（0=第1親, 1=第2親）をそのまま活用する。DB スキーマ変更なし。

### 追加するデータクラス（`graph_layout.py`）

```python
@dataclass(frozen=True)
class LayoutNode:
    commit: Commit
    x: float    # lane * 70 + 36
    y: float    # row_index * 60 + 145
    lane: int   # 追加フィールド

@dataclass(frozen=True)
class LayoutEdge:
    child_hash: str
    parent_hash: str
    # 変更なし

@dataclass(frozen=True)
class BranchLane:
    name: str
    lane: int
    tip_hash: str
    has_unique_commits: bool  # False = 波線表示
    connect_hash: str         # main レーン上の接続先コミットハッシュ
    x: float                  # lane * 70 + 36（テンプレート用）
```

---

## レーン割り当てアルゴリズム

### 関数シグネチャ

```python
def build_multi_lane_layout(
    rows: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
) -> tuple[list[LayoutNode], list[LayoutEdge], list[BranchLane]]:
```

### 処理ステップ

```
1. 行番号割り当て
   {hash: row_index} を rows の順序から構築

2. main レーン特定
   "main" または "master" の Branch を lane=0 に固定
   存在しない場合は rows[0].hash（最新コミット）の tip_hash と一致するブランチを使用
   それも存在しない場合は branches[0] を使用

3. main コミット集合の特定（_find_main_hashes）
   main 先端から CommitParent.position=0（第1親）を辿り
   visible set 内のハッシュを収集 → main_hashes: set[str]

4. 各ブランチの接続点特定（_find_connect_hash）
   ブランチ先端から position=0 を辿り、main_hashes に属する
   最初のコミットを connect_hash とする
   visible set 外に出た場合は rows[-1].hash（最古）を使用

5. has_unique_commits 判定
   tip_hash が main_hashes に含まれる → False
   それ以外 → True

6. レーン順ソート（_assign_lanes）
   connect_hash の row_index 昇順でソート
   → 接続点が上（新しい）ほど main の隣（内側）に配置
   → lane 1, 2, 3... を順に割り当て

7. 座標計算
   x = lane * 70 + 36
   y = row_index * 60 + 145
```

### 分割する小関数

| 関数 | 役割 |
| --- | --- |
| `_find_main_hashes` | main の第1親チェーンを収集 |
| `_find_connect_hash` | ブランチの main 接続点を特定 |
| `_assign_lanes` | ブランチをソートしてレーン番号を付与 |
| `_build_nodes` | LayoutNode リストを構築 |
| `_build_edges` | LayoutEdge リストを構築 |

150行制限のため、`graph_layout.py` が肥大する場合はファイル分割を検討する。

---

## cache_repo の追加関数

```python
def list_branches(session: Session, repo_id: str) -> list[Branch]:
    """リポジトリの全ブランチを返す。"""
```

---

## Router の変更（`html.py`）

```python
# graph_page 内
rows = cache_repo.list_recent_commits(session, rid, 50)
parents = cache_repo.parents_by_child(session, [r.hash for r in rows])
branches = cache_repo.list_branches(session, rid)
nodes, edges, branch_lanes = graph_layout.build_multi_lane_layout(
    rows, parents, branches
)
context = _build_graph_context(rid, rec, nodes, edges, branch_lanes)
```

`_build_graph_context` に追加するキー:

| キー | 値 |
| --- | --- |
| `branch_lanes` | `list[BranchLane]` |
| `svg_width` | `max(320, max_lane * 70 + 300)`（レーン幅 + テキスト領域 280px） |
| `lane_colors` | `LANE_COLORS` リスト |

---

## テンプレートの変更（`graph.html`）

### 変更箇所

1. `<svg>` の `viewBox` 横幅を `svg_width` に変更
2. ブランチ名ラベル（`{% for bl in branch_lanes %}`）を SVG 上部に追加
3. 波線（`has_unique_commits=False`）の描画を追加
4. コミット円の `cx` を `node.x`（lane ベース）に変更（現在は固定値 56）
5. ヘッダの説明文を「直近 50 コミット」に変更

---

## テスト方針

### 単体テスト（`tests/unit/test_graph_layout.py`）

| テストケース | 検証内容 |
| --- | --- |
| main のみのリポジトリ | lane=0 のみ、BranchLane が1件 |
| 2ブランチ（マージ済み） | 接続点ソートでレーン順が正しい |
| 独自コミットなしブランチ | `has_unique_commits=False`、connect_hash が正しい |
| 接続点が同じ行の2ブランチ | 順序が安定している（tip_hash で2次ソート） |
| visible set 外への接続 | `rows[-1].hash` にフォールバックする |

### E2E テスト（`tests/e2e/test_graph_smoke.py` に追加）

| テストケース | 検証内容 |
| --- | --- |
| マルチレーングラフが表示される | SVG 内に複数の `.commit-node` が存在する |

---

## 対象外（スコープ外）

- ブランチフィルタ（F-05）: 別タスクで対応
- リモートブランチ表示切り替え（F-11）: 別タスクで対応
- ページネーション時のレーン継続: 初期実装では50件の範囲内のみ対応
