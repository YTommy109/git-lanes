# コミットグラフ ビジュアル改善 設計書

<!-- derived-from ./docs/specification.md -->

作成日: 2026-04-29

---

## 概要

現在のコミットグラフは全ノードが同一スタイル・全ラインが同じ太さで描画されており、
GitUp のような洗練された見た目になっていない。
本設計では以下 3 点の改善を行い、ブランチの構造をより直感的に可視化する。

1. **ノード種別の区別** — TIP / ROOT / MERGE は中空円、通常は小さい塗りつぶし円
2. **メインライン強調** — HEAD が属するブランチラインを 4pt、その他を 2pt で描画
3. **バッジ形式ラベル** — ブランチ名・HEAD・タグを角丸バッジで表示

エッジ形状（直線）は現状のまま維持する。

---

## 設計方針

**アプローチ: テンプレート完結型**

Python 側はデータモデルに属性を追加するのみ。描画ロジックの条件分岐は Jinja2 テンプレートで完結させる。
データとビューの分離が明確で、今回の変更規模に対して過設計にならない。

---

## Section 1: データモデル変更（`graph_models.py`）

### NodeType の追加

```python
from typing import Literal

NodeType = Literal["tip", "root", "merge", "regular"]
```

| 値 | 条件 |
|----|------|
| `tip` | Layer 0 の実ノード（ブランチ先端） |
| `root` | 親コミットが存在しない（初回コミット） |
| `merge` | 親コミットが 2 つ以上（マージコミット） |
| `regular` | 上記以外の通常コミット |

### SvgLabel の追加

タグ・ブランチ・HEAD を区別するため、ラベルをラッピングするデータクラスを追加する。

```python
LabelKind = Literal["head", "branch", "tag"]

@dataclass
class SvgLabel:
    text: str
    kind: LabelKind
```

`_build_labels` の返り値を `dict[str, list[SvgLabel]]` に変更する。

### SvgNode への属性追加

```python
@dataclass
class SvgNode:
    cx: float
    cy: float
    color: str
    commit: Commit
    labels: list[SvgLabel]   # list[str] から変更
    node_type: NodeType = "regular"  # 追加
```

### SvgEdge への属性追加

```python
@dataclass
class SvgEdge:
    d: str
    color: str
    is_main: bool = False  # 追加: HEAD 所属ブランチのラインか
```

### GraphLine への属性追加

```python
@dataclass
class GraphLine:
    ...
    is_head_branch: bool = False  # 追加: HEAD ブランチのメインラインか
```

---

## Section 2: ノード種別判定とエッジ is_main（`graph_coords.py`）

### `_resolve_node_type` 関数を新設

```python
def _resolve_node_type(
    node: GraphNode,
    layer: GraphLayer,
    parents: dict[str, list[str]],
) -> NodeType:
    if layer.index == 0 and not node.dummy:
        return "tip"
    parent_hashes = parents.get(node.commit.hash, [])
    if not parent_hashes:
        return "root"
    if len(parent_hashes) >= 2:
        return "merge"
    return "regular"
```

### `_make_svg_node` の変更

`_resolve_node_type` を呼び出して `SvgNode.node_type` をセットする。

### `_make_svg_edges` の変更

`edge_is_main: dict[tuple[str, str], bool]` を `edge_colors` と同様に `graph_builder_phases.py` の `_place_parent` 内で構築する。
第 1 親（`i == 0`、同一ライン継続）かつ `line.is_head_branch == True` のエッジを `True` として記録する。
`_make_svg_edges` はこの dict を参照して `SvgEdge.is_main` をセットする。

---

## Section 3: HEAD ブランチ追跡（`graph_builder.py`）

### `_build_layer0` の変更

Layer 0 構築時、`tip.hash == head_hash` のノードの `primary_line` に `is_head_branch = True` をセットする。

```python
line = GraphLine(branch=branch, color=color, is_main=True)
if tip.hash == head_hash:
    line.is_head_branch = True
```

**スコープ外**: detached HEAD（HEAD がブランチ先端でない場合）は今回対応しない。

---

## Section 4: テンプレート変更（`graph.html`）

### エッジ描画

```html
<path d="{{ edge.d }}"
      stroke="{{ edge.color }}"
      stroke-width="{% if edge.is_main %}4{% else %}2{% endif %}"
      fill="none"/>
```

### ノード描画（種別ごとの条件分岐）

| node_type | 描画 |
|-----------|------|
| `tip`, `root` | 中空円 r=9, stroke-width=2.5 |
| `merge` | 中空円 r=7, stroke-width=2.5 |
| `regular` | 塗りつぶし円 r=5 |

### バッジラベル描画

`node.labels` は `SvgLabel` のリストで、`label.kind` で種別を判定する。

| `label.kind` | 描画 |
|---|---|
| `head` | ブランチ色の不透明バッジ、白太字テキスト |
| `branch` | ブランチ色の半透明バッジ（opacity=0.65）、白テキスト |
| `tag` | 枠線のみ（fill=none）のピル形バッジ（rx=7）、グレーテキスト |

バッジ幅はラベル文字数から動的計算: `(label.text | length) * 7 + 8` px

---

## 変更対象ファイルまとめ

| ファイル | 変更内容 |
|----------|----------|
| `backend/services/graph_models.py` | `NodeType`・`LabelKind`・`SvgLabel` 型追加、`SvgNode.node_type`・`SvgEdge.is_main`・`GraphLine.is_head_branch` 追加、`SvgNode.labels` 型変更 |
| `backend/services/graph_coords.py` | `_resolve_node_type` 新設、`_make_svg_node`・`_make_svg_edges` 修正 |
| `backend/services/graph_builder.py` | `_build_layer0` に HEAD ブランチフラグセット処理追加、`_build_labels` の返り値を `list[SvgLabel]` に変更 |
| `backend/services/graph_builder_phases.py` | `_place_parent` で `edge_is_main` dict を構築、`build_layers` の返り値に追加 |
| `backend/templates/graph.html` | ノード種別描画・バッジラベル種別・エッジ太さの条件分岐追加 |

---

## スコープ外

- エッジのベジエ曲線化（ユーザーが直線を選択）
- Detached HEAD 対応
- 仮想ライン（破線）の実装
- タグバッジの SVG `<text>` 幅計算（フォントメトリクス非依存の概算式で対応）
