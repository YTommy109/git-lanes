# ブランチラベル縦積み表示 設計書

<!-- derived-from ./docs/specification.md -->
<!-- constrained-by ./docs/architecture.md -->

## 概要

同一レーンに複数のブランチ名・タグが存在する場合、カンマ区切りの1行表示から縦積み（1ラベル1行）表示に変更する。GitUp のような視認性の高いレイアウトを実現する。

## 問題

現在の実装では `SvgBranchHeader.display_text` に全ラベルをカンマ結合した文字列を格納し、1つの `<text>` 要素で表示している。ラベルが複数あると表示エリアが不足して見切れる。

## 要件

- 同一レーンの複数ラベルを縦方向（上方向）に積み上げて表示する
- 各ラベルは独立した `<text>` 要素で描画する
- ラベル間隔は既存の `GRID_SPACING = 30px` を使用する
- 現行の `GRID_ORIGIN_Y = 102` で最大3ラベルまでを正の Y 座標に収める
- ダミーノード用のコネクター（白丸マーカー）は変更しない

## 設計

### 1. `SvgBranchHeader` の変更

<!-- constrained-by ./docs/architecture.md -->

`backend/services/graph_models.py` の `SvgBranchHeader` を以下のように変更する。

**削除するフィールド:**
- `cy: float` — `label_entries` で代替
- `labels: list[SvgLabel]` — `label_entries` で代替
- `display_text: str` — カンマ結合の元凶、不要になる

**追加するフィールド:**
- `label_entries: list[tuple[float, SvgLabel]]` — `(cy, label)` のペアのリスト。インデックス 0 が最下段（コミット行に最近接）

```python
@dataclass
class SvgBranchHeader:
    """SVG ヘッダー行に描画するブランチ名ラベル。"""

    cx: float
    color: str
    label_entries: list[tuple[float, SvgLabel]]
    connector_to_x: float | None = None
    connector_to_y: float | None = None
```

### 2. `build_svg_headers()` の変更

`backend/services/grid_svg_parts.py` の `build_svg_headers()` で各ラベルの cy を算出する。

```
インデックス i のラベルの cy = GRID_ORIGIN_Y - (i + 1) * GRID_SPACING
  i=0（最下段）: 102 - 30 = 72
  i=1:           102 - 60 = 42
  i=2:           102 - 90 = 12
```

connector_to_x / connector_to_y はヘッダー単位で管理し、変更しない。

### 3. テンプレートの変更

`backend/templates/graph.html` のブランチ名描画ループを変更する。

変更前（1ラベル1行、カンマ結合）:
```html
{% for header in branch_headers %}
  <text transform="translate({{ header.cx }}, {{ header.cy - 14 }}) rotate(-45)"
        ...>{{ header.display_text }}</text>
{% endfor %}
```

変更後（複数ラベル縦積み）:
```html
{% for header in branch_headers %}
  {% for label_cy, label in header.label_entries %}
    <text transform="translate({{ header.cx }}, {{ label_cy - 14 }}) rotate(-45)"
          ...>{{ label.text }}</text>
  {% endfor %}
{% endfor %}
```

### 4. 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `backend/services/graph_models.py` | 修正 | `SvgBranchHeader` のフィールド変更 |
| `backend/services/grid_svg_parts.py` | 修正 | `build_svg_headers()` で per-label cy を計算 |
| `backend/templates/graph.html` | 修正 | `label_entries` ループで縦積み描画 |
| `tests/unit/test_grid_svg_parts.py` | 新規 | `build_svg_headers()` の縦積み出力を検証 |

### 5. テスト戦略

#### 単体テスト（`tests/unit/test_grid_svg_parts.py`）

- 1ラベルのとき `label_entries` が1件で cy = 72
- 2ラベルのとき `label_entries` が2件で cy = 72, 42（インデックス 0 が最下段）
- 3ラベルのとき `label_entries` が3件で cy = 72, 42, 12
- ダミーノードがある場合に `connector_to_x`/`connector_to_y` が設定される
- ダミーノードがない場合に connector が None

#### 統合テスト

既存の統合テストで HTML 出力にブランチ名が含まれることを確認済みのため、既存テストが通ることで回帰を検出する。

## 制約

- `GRID_ORIGIN_Y = 102` は変更しない（3ラベルまで収まる）
- 4ラベル以上への対応（動的ヘッダー高さ）は別タスクとして切り出す
- JavaScript・D3.js は使用しない
