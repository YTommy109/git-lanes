# キーボードナビゲーション設計書

<!-- derived-from ./docs/specification.md -->
<!-- constrained-by ./docs/architecture.md -->

## 概要

コミットグラフ上で矢印キーによるノード選択ナビゲーションを実現する。
マウスクリックと同等の操作を、上下左右キーでレーン/行の交点を移動するイメージで提供する。

## 要件

- 上下左右キーでコミットノード間を移動できる
- 選択できるのはコミットノード（`.commit-node`）のみ
- **↑↓**: 同じレーン内で行を移動（同レーンの前後コミット）
- **←→**: 隣レーンへ移動（lane ± 1、なければ ±2…）し、行差が最小のコミットを選択
- グラフ下端に達したとき、次ページをロードして移動を継続する
- スペースキーでクリックと同等の詳細表示を発火する

## 設計

### 1. データ層：SvgNode への lane/row 追加

<!-- constrained-by ./docs/architecture.md -->

`backend/services/graph_models.py` の `SvgNode` に `lane: int` と `row: int` を追加する。

```python
@dataclass
class SvgNode:
    cx: float
    cy: float
    lane: int        # 追加
    row: int         # 追加
    color: str
    commit: Commit
    labels: list[SvgLabel]
    node_type: NodeType
```

`to_svg()` 変換時に `GridNode.lane` と `GridNode.row` をそのまま渡す。

### 2. テンプレート：data 属性の付与

`backend/templates/graph.html` の `.commit-node` 要素に属性を追加する。

```html
<g class="commit-node"
   data-lane="{{ node.lane }}"
   data-row="{{ node.row }}"
   data-msg="..."
   ...>
```

### 3. フォーカス管理

SVG コンテナ（`#graph-container`）に `tabindex="0"` を付与し、フォーカスがある間だけキーイベントを受け付ける。グラフ外クリックでフォーカスが外れたとき、ナビゲーションは無効化される。

### 4. ナビゲーションロジック（graph-keyboard.js）

`static/js/graph-keyboard.js` に集中したロジックを実装する（目安 50〜80 行）。

#### 隣接ノード探索アルゴリズム

**↑（上方向）**
1. 現在の `(lane, row)` を取得
2. 同レーンの全ノードから `row < current_row` のノードを抽出
3. `row` が最大（直近）のノードを選択

**↓（下方向）**
1. 現在の `(lane, row)` を取得
2. 同レーンの全ノードから `row > current_row` のノードを抽出
3. `row` が最小（直近）のノードを選択
4. なければページロード処理へ

**←（左方向）/ →（右方向）**
1. 方向に応じて `target_lane = lane - 1` または `lane + 1`
2. `target_lane` のノードが存在しなければ ±1 ずつ拡大して探す（最大レーン数まで）
3. `target_lane` 内の全ノードから `|row - current_row|` が最小のノードを選択

#### ページロード処理

↓で次ノードが見つからないとき：

1. ページ末尾の htmx センチネル要素（`[hx-trigger*="intersect"]`）を取得
2. `element.scrollIntoView()` で表示域に入れ、htmx の intersect を発火
3. `htmx:afterSettle` イベントを一度だけ購読し、再度↓ナビゲーションを実行

#### 選択の実行

ターゲットノードが見つかったら `node.click()` を呼び出し、既存の hyperscript ハンドラ（`.selected` クラス切り替え + htmx detail fetch）をそのまま再利用する。

**スペースキー**: 現在選択中のノード（`.commit-node.selected`）に対して `click()` を発火し、詳細パネルを再表示する。選択ノードがなければ何もしない。

#### ページロードのリトライ

`htmx:afterSettle` 後に再試行するのは 1 回のみ。ロード後にも同レーンの次ノードがなければ移動しない（ページ末端と判断）。

### 5. ファイル構成

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `backend/services/graph_models.py` | 修正 | `SvgNode` に `lane`, `row` を追加 |
| `backend/services/graph_service.py` | 修正 | `to_svg()` で `lane`, `row` を渡す |
| `backend/templates/graph.html` | 修正 | `data-lane`, `data-row` 属性を付与、`tabindex="0"` を追加 |
| `static/js/graph-keyboard.js` | 新規 | キーボードナビゲーションロジック |
| `backend/templates/base.html` | 修正 | `graph-keyboard.js` を読み込む |
| `tests/unit/test_svg_node_lane_row.py` | 新規 | `to_svg()` の lane/row 付与を検証する単体テスト |

### 6. テスト戦略

#### 単体テスト（Python・`tests/unit/test_svg_node_lane_row.py`）

`to_svg()` による `lane`/`row` 付与を検証する（ナビゲーションロジックは JS 側のため Python テストの対象外）。

- `to_svg()` が `GridNode.lane`/`GridNode.row` を `SvgNode.lane`/`SvgNode.row` に正しく渡すこと
- 複数ページにまたがるグラフでも行番号が一意で連続すること

#### E2E テスト（Playwright）

- 初期状態でグラフにフォーカスを当て、↓キーで次のコミットが選択されること
- →キーで隣レーンの最近接コミットが選択されること
- ページ末尾で↓キーを押すと次ページがロードされ、コミットが選択されること

## 制約

- JavaScript は最小限（`graph-keyboard.js` のみ、`app.js` は作らない）
- D3.js 不使用
- Git 操作は既存の pygit2 実装を変更しない
- hyperscript の既存クリックハンドラは変更しない（`click()` 呼び出しで再利用）
