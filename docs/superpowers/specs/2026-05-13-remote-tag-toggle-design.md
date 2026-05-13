# リモート・タグ表示トグル 設計仕様

<!-- derived-from ./docs/specification.md -->

## 概要

グラフ画面の右上にトグルボタンを追加し、リモートブランチとタグラベルの表示/非表示を切り替える。

## 決定事項

| 項目 | 決定内容 |
|---|---|
| ボタン配置 | `<header>` 内に inline。リポジトリ名を左端、トグルボタン群を右端に flex 配置 |
| ボタンラベル | "Remote" と "Tag" の 2 つ |
| ON スタイル | 青枠（`#4285f4`）＋薄青背景（`#e8f0fe`）、青文字・太字 |
| OFF スタイル | グレー枠（`#ccc`）＋白背景、グレー文字（`#999`） |
| 更新方式 | htmx サーバー再レンダリング（`hx-select` による部分スワップ） |
| 状態管理 | URL クエリパラメータ（`show_remote`, `show_tags`）。リロード後も状態維持 |
| デフォルト | 両方 ON（現在の挙動を維持） |

## アーキテクチャ

```
ユーザーがトグルをクリック
→ hx-get /repos/{id}/graph?show_remote=0&show_tags=1
→ FastAPI: Query パラメータで受け取る
→ graph_service がブランチ・タグをフィルタして SVG 再構築
→ htmx: hx-select="#graph-main" でレスポンスから <main> のみ抜き出しスワップ
→ hx-push-url="true" で URL 更新
```

## 変更ファイル

### `backend/routers/html.py`

`graph_page` に `show_remote: bool = True` と `show_tags: bool = True` の Query パラメータを追加する。

```python
@router.get("/repos/{repo_id}/graph", response_class=HTMLResponse)
async def graph_page(
    request: Request,
    repo_id: str,
    show_remote: bool = True,
    show_tags: bool = True,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    ...
    result = graph_service.sync_and_build(
        session, rid, rec.path,
        show_remote=show_remote,
        show_tags=show_tags,
    )
    context = {
        ...
        "show_remote": show_remote,
        "show_tags": show_tags,
    }
```

### `backend/services/graph_service.py`

`sync_and_build` に `show_remote` と `show_tags` を追加する。

- `show_remote=False` のとき: `filter_synced_remote_branches` 適用後、さらにリモートブランチを全除外
- `show_tags=False` のとき: `tag_repo.list_tags` を呼ばず空リストを渡す

```python
def sync_and_build(
    session: Session,
    repo_id: str,
    repo_path: str,
    show_remote: bool = True,
    show_tags: bool = True,
) -> GraphResult:
    ...
    branches = filter_synced_remote_branches(branch_repo.list_branches(session, repo_id))
    if not show_remote:
        branches = [b for b in branches if b.is_remote == 0]
    tags = tag_repo.list_tags(session, repo_id) if show_tags else []
    return grid_builder.build_grid(rows, parents, branches, tags, fork_data)
```

### `backend/templates/graph.html`

1. `<main>` に `id="graph-main"` を付与（htmx スワップターゲット）
2. `<header>` を flex レイアウトに変更
3. トグルボタンを追加

```html
<main id="graph-main" class="l--flex" style="height: 100%">
  <section ...>
    <header style="display:flex;justify-content:space-between;align-items:center">
      <h1>{{ repo_name }}</h1>
      <div style="display:flex;gap:8px">
        <button
          hx-get="/repos/{{ repo_id }}/graph?show_remote={{ 0 if show_remote else 1 }}&show_tags={{ 1 if show_tags else 0 }}"
          hx-target="#graph-main"
          hx-swap="outerHTML"
          hx-select="#graph-main"
          hx-push-url="true"
          class="toggle-btn{% if not show_remote %} is-off{% endif %}"
        >Remote</button>
        <button
          hx-get="/repos/{{ repo_id }}/graph?show_remote={{ 1 if show_remote else 0 }}&show_tags={{ 0 if show_tags else 1 }}"
          hx-target="#graph-main"
          hx-swap="outerHTML"
          hx-select="#graph-main"
          hx-push-url="true"
          class="toggle-btn{% if not show_tags %} is-off{% endif %}"
        >Tag</button>
      </div>
    </header>
    ...
```

### `static/css/style.css`

トグルボタンの ON/OFF スタイルを追加する。

```css
.toggle-btn {
  border: 2px solid #4285f4;
  border-radius: 14px;
  padding: 4px 14px;
  font-size: 12px;
  background: #e8f0fe;
  color: #4285f4;
  font-weight: 600;
  cursor: pointer;
}

.toggle-btn.is-off {
  border: 1px solid #ccc;
  background: #fff;
  color: #999;
  font-weight: normal;
}
```

## テスト方針

### 単体テスト（`tests/unit/routers/test_html.py` または `tests/unit/services/test_graph_service.py`）

- `show_remote=False` を渡したとき `b.is_remote == 1` のブランチが除外される
- `show_tags=False` を渡したとき tags が空リストになる
- パラメータなし（デフォルト）で両方 `True` になる

### 手動確認

1. グラフ画面を開き、両トグルが ON（青）であることを確認
2. Remote ボタンをクリック → リモートブランチのレーンが消え、URL が `?show_remote=false` を含む
3. Tag ボタンをクリック → タグバッジが消え、URL が `?show_tags=false` を含む
4. リロードしてもトグル状態が維持されることを確認

## 対象外

- トグル状態のサーバー側永続化（DB 保存）
- ユーザーごとのデフォルト設定
