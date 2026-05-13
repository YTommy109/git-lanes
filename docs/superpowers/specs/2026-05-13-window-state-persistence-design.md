# ウィンドウ状態永続化 — 設計書

<!-- derived-from ./docs/architecture.md -->

## 概要

Git Lanes を再起動するたびにウィンドウが初期位置・初期サイズで表示される問題を解消する。
終了前のウィンドウ位置・サイズ・表示リポジトリ・アクティブコミットを JSON に保存し、
次回起動時に復元する。

---

## 保存する状態

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `x` | `int \| None` | `None` | ウィンドウ左上 X 座標（`None` は OS 任せ） |
| `y` | `int \| None` | `None` | ウィンドウ左上 Y 座標 |
| `width` | `int` | `1280` | ウィンドウ幅 |
| `height` | `int` | `800` | ウィンドウ高さ |
| `repo_id` | `str \| None` | `None` | 最後に表示していたリポジトリ ID |
| `commit_hash` | `str \| None` | `None` | 詳細パネルで選択していたコミットハッシュ |
| `show_remote` | `bool` | `True` | リモートブランチ表示トグル |
| `show_tags` | `bool` | `True` | タグ表示トグル |

保存先: `~/Library/Application Support/git-lanes/window_state.json`
（`GIT_LANES_DATA_DIR` 環境変数が設定されている場合はその配下）

---

## アーキテクチャ

### 起動フロー

```
app.py:main()
  1. state_store.load() で WindowState を読み込む
  2. create_window(x, y, width, height) で位置・サイズを復元
  3. repo_id があれば初期 URL を /repos/{repo_id}/graph?... に設定
     なければ / （ウェルカム画面）
  4. window.events.moved   → _on_window_move()   → デバウンス保存
     window.events.resized → _on_window_resize() → デバウンス保存
  5. webview.start() ブロック
```

### 実行中の状態保存

pywebview イベント（ウィンドウ移動・リサイズ）:
- `_on_window_move(x, y)` / `_on_window_resize(width, height)` が呼ばれる
- `threading.Timer(0.5, ...)` でデバウンス（500ms 後に書き込み）
- 既存タイマーがあればキャンセルして新しいタイマーをセット

FastAPI ハンドラー（サーバーサイド副作用）:
- `graph_page()`: `repo_id`, `show_remote`, `show_tags` を保存
- `commit_detail()`: `commit_hash` を保存

### 詳細パネルの初期描画

`graph_page()` に `active_commit: str | None = Query(None)` を追加。
`active_commit` が指定された場合:
- `commit_repo.get_commit()` で詳細を取得してテンプレートに渡す
- `partials/detail.html` を `initial_detail` コンテキストとして埋め込む
- `graph.html` 内の `#commit-detail` を即時描画する

### スクロール復元

`<g class="commit-node">` に `id="node-{node.commit.hash}"` を追加。
`active_commit` が渡された場合、`graph.html` 末尾に以下を追加：

```html
<div hidden
  _="on load
       set el to document.getElementById('node-{{ active_commit }}')
       if el then el.scrollIntoView({block: 'center'}) end">
</div>
```

---

## ファイル変更一覧

| ファイル | 種別 | 変更内容 |
|---|---|---|
| `backend/state_store.py` | 新規 | `WindowState` dataclass, `load()`, `save()` |
| `backend/paths.py` | 修正 | `window_state_path()` 追加 |
| `backend/app.py` | 修正 | 状態読み込み・pywebview イベント登録・デバウンス保存 |
| `backend/routers/html.py` | 修正 | `graph_page` / `commit_detail` で状態保存、`active_commit` パラメータ追加 |
| `backend/templates/graph.html` | 修正 | コミットノードに `id` 追加、hyperscript スクロール追加 |

---

## テスト戦略

### 単体テスト（`tests/unit/test_state_store.py`）

| ケース | 内容 |
|---|---|
| `test_load_returns_defaults_when_file_missing` | JSON 不在 → デフォルト値を返す |
| `test_load_returns_defaults_when_file_is_corrupt` | 壊れた JSON → デフォルト値を返す |
| `test_load_returns_saved_values` | 正常な JSON → 保存済み値を返す |
| `test_save_writes_json_file` | `save()` が JSON ファイルを書く |
| `test_round_trip` | `save()` → `load()` で値が一致する |
| `test_save_merges_partial_update` | 一部フィールドだけ更新しても他フィールドが保たれる |

### `html.py` の単体テスト追加

| ケース | 内容 |
|---|---|
| `test_graph_page_saves_state` | `graph_page` 呼び出し後に JSON が更新される |
| `test_commit_detail_saves_commit_hash` | `commit_detail` 呼び出し後に `commit_hash` が保存される |
| `test_graph_page_with_active_commit_renders_detail` | `active_commit` が渡されると詳細パネルが描画される |

---

## 制約・注意事項

- `state_store.py` の `save()` はスレッドセーフに書く（`threading.Lock` 使用）
- JSON 書き込みはアトミックに行う（`tmp` ファイルに書いてから `rename`）
- `commit_hash` の保存は既存の `parse_commit_hash()` バリデーションを通す
- `x`, `y` が画面外になる場合（ディスプレイ構成変更等）への対処は v1 スコープ外とし、OS に任せる（pywebview が画面外ウィンドウを自動補正する）
