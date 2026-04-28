# グラフ描画アルゴリズム全面書き換え 設計仕様

日付: 2026-04-28

## 背景と目的

### 現状の問題

現在の実装（`graph_layout.py` + `lane_assignment.py`）はブランチ名ベースで静的にレーンを割り当てる。
そのため、マージ済みブランチ（ブランチ参照が消えたもの）のコミットはレーンが割り当てられず、
マージコミットの第 2 親チェーンが描画されない。結果として、グラフが直線的に見え、
実際には存在するコミットが表示されないように見える。

### 目的

- すべてのコミット（マージ済みブランチのコミット含む）を正確に描画する
- gitup（macOS Git GUI）の `GIGraph` アルゴリズムを Python で再実装する
- 後方互換性は捨て、クリーンな設計にする

---

## 採用しないアプローチ

- **局所パッチ**: 既存コードにマージ検出を追加する方法。技術的負債が増え、複雑なケースで再び壊れるリスクが高いため不採用。
- **段階的移行（インターフェース保持）**: SVG 出力形式を維持したまま中身を書き換える方法。変換層が増えて複雑になるため不採用。

---

## 設計方針

- **git → SQLite → グラフ** のパイプラインは変更しない。グラフ構築層だけを置き換える。
- SQLite から読んだコミット・ブランチ・タグ情報を入力とし、SVG 描画用の座標付きデータを出力する。
- ページングは対象外（当面、数万件コミットのリポジトリは使用しない）。

---

## ファイル構成

### 削除

| ファイル | 理由 |
|---|---|
| `backend/services/graph_layout.py` | 全面置き換え |
| `backend/services/lane_assignment.py` | 全面置き換え |
| `backend/services/lane_nodes.py` | 全面置き換え |
| `backend/services/topo_sort.py` | Phase 3 のループに内包 |

### 新規作成

| ファイル | 役割 |
|---|---|
| `backend/services/graph_models.py` | データ構造（GraphLayer / GraphNode / GraphLine / GraphBranch / SvgNode / SvgEdge） |
| `backend/services/graph_builder.py` | BUILD_GRAPH アルゴリズム本体（Phase 1〜3 + SVG 変換） |
| `backend/services/graph_coords.py` | Phase 4: X/Y 座標計算（150 行制限のため分離） |

### 更新

| ファイル | 変更内容 |
|---|---|
| `backend/routers/html.py` | `graph_builder.build_graph()` を呼ぶよう差し替え |
| `backend/templates/graph.html` | `SvgNode` / `SvgEdge` の新形式に対応 |

---

## データ構造（graph_models.py）

```python
@dataclass
class GraphBranch:
    main_line: GraphLine
    tip_node: GraphNode
    refs: list[str]          # ブランチ名・タグ名のリスト

@dataclass
class GraphLine:
    branch: GraphBranch
    nodes: list[GraphNode]
    x: float = 0.0           # レイヤー間で引き継ぐ X 座標（ライン継続性）
    color: str = "#4a9cf6"   # GraphBranch 生成時にパレットから割り当て
    is_main: bool = False    # ブランチの main ライン（+2 スペース付与）

@dataclass
class GraphNode:
    commit: Commit           # SQLite の Commit モデル
    layer: GraphLayer
    primary_line: GraphLine
    dummy: bool = False      # 子が未確定のプレースホルダー
    x: float = 0.0
    parent_nodes: list[GraphNode] = field(default_factory=list)

@dataclass
class GraphLayer:
    index: int
    nodes: list[GraphNode] = field(default_factory=list)
    lines: list[GraphLine] = field(default_factory=list)
    y: float = 0.0

# SVG テンプレートへ渡す出力形式
@dataclass
class SvgNode:
    cx: float
    cy: float
    color: str
    commit_hash: str
    labels: list[str]        # ブランチ名・タグ名

@dataclass
class SvgEdge:
    d: str                   # SVG path の d 属性（M/L/C コマンド）
    color: str

@dataclass
class GraphResult:
    nodes: list[SvgNode]
    edges: list[SvgEdge]
    canvas_width: float
    canvas_height: float
```

---

## アルゴリズム詳細

### Phase 1 — TIP 収集（graph_builder.py）

**入力**: SQLite から取得した branches / tags / commits
**出力**: `list[Commit]`（TIP コミット、重複除去済み）

優先順位: HEAD → ローカルブランチ → リモートブランチ → タグ
同一コミットを指す複数の参照は 1 エントリに統合する。

### Phase 2 — Layer 0 生成（graph_builder.py）

**入力**: Phase 1 の TIP リスト
**出力**: `GraphLayer(index=0)` + `commit_to_node: dict[str, GraphNode]` の初期状態

各 TIP に対して `GraphBranch + GraphLine + GraphNode` を 1 セット生成する。
色はブランチ生成順に `LANE_COLORS` パレットから割り当てる。

`dummy` の判定: TIP コミットが他の TIP の祖先になっている場合（例: main が feat の第 1 親）、
その TIP は Layer 0 時点でまだ子（feat TIP）が同レイヤーに存在するため `dummy=True` となる。
`commit_to_children` を参照し、すべての子がすでに別レイヤーに確定済みなら `dummy=False`。

### Phase 3 — 層状構造の繰り返し構築（graph_builder.py）

**入力**: 前レイヤー `prev_layer`、`commit_to_node`、`commit_to_children`
**出力**: 新しい `GraphLayer`（空なら終了）

`commit_to_children: dict[str, list[str]]` は Phase 1 の前に SQLite の parents テーブルから構築する。
`{parent_hash: [child_hash, ...]}` の形式。

ループ内の処理:

```
for node in prev_layer.nodes:
    if node.dummy:
        if all_children_on_different_layer(node.commit):
            # 実ノードに昇格して curr_layer に追加
        else:
            # ダミーのまま curr_layer に持ち越し
    else:
        for i, parent in enumerate(node.commit.parents):
            line = node.primary_line if i == 0 else new GraphLine()
            # i > 0 はマージの第 2 親以降 → 新しいラインを生成
            if parent in commit_to_node:
                line.add(existing_node)   # 既存ノードに接続するだけ
            else:
                ready = all_children_on_different_layer(parent)
                new GraphNode(parent, curr_layer, line, dummy=not ready)
```

「準備完了」の判定:

> あるコミットのすべての子コミットが、すでに別のレイヤーにノードとして存在する

### Phase 4 — 座標計算（graph_coords.py）

**入力**: `list[GraphLayer]`
**出力**: 各 `GraphNode.x` と `GraphLayer.y` に値を付与（インプレース更新）

```
SPACING_X = 30
SPACING_Y = 60

for layer in layers:
    layer.y = layer.index * SPACING_Y
    last_x = 0
    for node in layer.nodes:
        x = node.primary_line.x        # ライン継続性：前レイヤーの X を引き継ぐ
        if node.primary_line.is_main:
            last_x += 2                # main ラインは視認性のため追加スペース
        if x <= last_x:
            x = last_x + 1            # 衝突回避
        node.x = x
        node.primary_line.x = x
        last_x = x
```

### SVG 変換（graph_builder.py の最終ステップ）

座標付きの `list[GraphLayer]` を走査し、`list[SvgNode]` と `list[SvgEdge]` に変換する。

- **SvgNode**: `cx = node.x * SPACING_X`、`cy = layer.y`、カラーはライン色
- **SvgEdge**: 各ラインのノード列を SVG `path` の `d` 文字列に変換する。
  異レイヤー間は直線（`L`）、同レーン内も直線。曲線（`C`）は後フェーズで検討。

---

## データフロー

```
SQLite (commits / branches / tags)
    ↓
[Phase 1] TIP 収集          → list[Commit]
    ↓
[Phase 2] Layer 0 生成      → GraphLayer(0) + commit_to_node
    ↓
[Phase 3] 層状構造構築      → list[GraphLayer]（ダミーノード解決済み）
    ↓
[Phase 4] 座標計算          → 各 node.x, layer.y に値付与
    ↓
[SVG変換] SvgNode/SvgEdge生成
    ↓
Jinja2 テンプレート → SVG レスポンス
```

---

## テスト方針

- `graph_builder.py` と `graph_coords.py` は純粋関数として実装し、単体テストを書く
- テストケース:
  - 直線履歴（ブランチなし）
  - 1 本のフィーチャーブランチ + マージ
  - マージ済みブランチ（ブランチ参照なし）の第 2 親チェーン
  - ダミーノードが必要なケース（複数 TIP から同一コミットに収束）
- E2E テストは Phase 2 実装完了後に追加

---

## 実装ロードマップ

| Phase | 内容 | 完了条件 |
|---|---|---|
| Phase 1 | `graph_models.py` + `graph_builder.py` の Phase 1〜3 + `graph_coords.py` | 単体テストがすべて通る |
| Phase 2 | `html.py` / `graph.html` の更新、既存テストの修正 | アプリ起動してグラフが表示される |
| Phase 3 | SVG の視覚的改善（曲線エッジ・色・間隔調整） | 目視確認 |
