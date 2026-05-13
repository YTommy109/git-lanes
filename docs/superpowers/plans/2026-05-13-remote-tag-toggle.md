# リモート・タグ表示トグル 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** グラフ画面の右上に Remote / Tag トグルボタンを追加し、リモートブランチとタグラベルの表示/非表示を切り替えられるようにする。

**Architecture:** FastAPI エンドポイントに `show_remote` / `show_tags` クエリパラメータを追加し、`graph_service.sync_and_build` 内でブランチ・タグをフィルタして SVG を再構築する。htmx の `hx-select` でページ全体ではなく `<main id="graph-main">` だけを差し替え、`hx-push-url` で URL に状態を保持する。

**Tech Stack:** Python 3.12 / FastAPI / SQLModel / Jinja2 / htmx 2.x / pytest / unittest.mock

---

### Task 1: graph_service.sync_and_build にフィルタパラメータを TDD で追加

**Files:**
- Modify: `backend/services/graph_service.py`
- Create: `tests/unit/test_graph_service_filter.py`

- [ ] **Step 1: テストファイルを作成して失敗させる**

`tests/unit/test_graph_service_filter.py` を以下の内容で作成する。

```python
"""graph_service のフィルタパラメータのテスト。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.models import Branch
from backend.services.graph_service import sync_and_build


def _local(name: str, tip: str = "aaa") -> Branch:
    return Branch(name=name, repo_id="r1", tip_hash=tip, is_remote=0)


def _remote(name: str, tip: str = "bbb") -> Branch:
    # tip を local と意図的に変えて filter_synced_remote_branches で除外されないようにする
    return Branch(name=name, repo_id="r1", tip_hash=tip, is_remote=1)


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags", return_value=[])
@patch("backend.services.graph_service.branch_repo.list_branches")
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_show_remote_falseのときリモートブランチが除外される(
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
    mock_list_branches.return_value = [_local("main"), _remote("origin/main")]
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path", show_remote=False)

    # --- Assert ---
    branches_arg = mock_build.call_args[0][2]
    assert all(b.is_remote == 0 for b in branches_arg)


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags")
@patch("backend.services.graph_service.branch_repo.list_branches", return_value=[])
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_show_tags_falseのときタグが空リストで渡される(
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
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path", show_tags=False)

    # --- Assert ---
    tags_arg = mock_build.call_args[0][3]
    assert tags_arg == []
    mock_list_tags.assert_not_called()


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags", return_value=[])
@patch("backend.services.graph_service.branch_repo.list_branches", return_value=[])
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_デフォルトではshow_remoteとshow_tagsがともにtrueになる(
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
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path")

    # --- Assert ---
    # tag_repo.list_tags が呼ばれていれば show_tags=True が維持されている
    mock_list_tags.assert_called_once()
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```bash
uv run pytest tests/unit/test_graph_service_filter.py -v
```

期待: `TypeError: sync_and_build() got an unexpected keyword argument 'show_remote'` 相当のエラーで FAIL。

- [ ] **Step 3: graph_service.sync_and_build にパラメータとフィルタを実装する**

`backend/services/graph_service.py` を以下に変更する（関数シグネチャと本体のみ変更、他はそのまま）:

```python
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
    branches = filter_synced_remote_branches(branch_repo.list_branches(session, repo_id))
    if not show_remote:
        branches = [b for b in branches if b.is_remote == 0]
    tags = tag_repo.list_tags(session, repo_id) if show_tags else []
    _logger.debug(
        "グラフ描画: repo_id=%s commits=%d branches=%d", repo_id, len(rows), len(branches)
    )
    fork_data = compute_fork_data(rows, parents, branches)
    persist_fork_points(session, branches, fork_data)
    return grid_builder.build_grid(rows, parents, branches, tags, fork_data)
```

- [ ] **Step 4: テストを実行して PASS を確認する**

```bash
uv run pytest tests/unit/test_graph_service_filter.py -v
```

期待: 3 テストすべて PASS。

- [ ] **Step 5: 既存テストが壊れていないことを確認する**

```bash
uv run pytest tests/unit/ -v
```

期待: すべて PASS。

- [ ] **Step 6: コミットする**

```bash
git add backend/services/graph_service.py tests/unit/test_graph_service_filter.py
git commit -m "feat: graph_service に show_remote/show_tags フィルタパラメータを追加する"
```

---

### Task 2: html.py ルーターに show_remote / show_tags クエリパラメータを追加

**Files:**
- Modify: `backend/routers/html.py`

- [ ] **Step 1: html.py の graph_page を変更する**

`backend/routers/html.py` の `graph_page` 関数を以下に置き換える（`show_remote`, `show_tags` パラメータを追加し、`graph_service.sync_and_build` に渡して context に含める）:

```python
@router.get("/repos/{repo_id}/graph", response_class=HTMLResponse)
async def graph_page(
    request: Request,
    repo_id: str,
    show_remote: bool = True,
    show_tags: bool = True,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ブランチグラフ画面を返す。"""
    rid = parse_repo_id(repo_id)
    rec = repository_repo.get_repository(session, rid)
    if rec is None:
        raise RepositoryNotFoundError
    result = graph_service.sync_and_build(
        session, rid, rec.path,
        show_remote=show_remote,
        show_tags=show_tags,
    )
    context: dict = {
        "repo_id": rid,
        "repo_name": rec.name,
        "nodes": result.nodes,
        "edges": result.edges,
        "branch_headers": result.branch_headers,
        "svg_width": result.canvas_width,
        "svg_height": result.canvas_height,
        "repos": repository_repo.list_repositories(session),
        "current_repo_id": rid,
        "show_remote": show_remote,
        "show_tags": show_tags,
    }
    return templates.TemplateResponse(request, "graph.html", context)
```

- [ ] **Step 2: 型チェックを実行して問題がないことを確認する**

```bash
uv run task typecheck
```

期待: エラーなし。

- [ ] **Step 3: コミットする**

```bash
git add backend/routers/html.py
git commit -m "feat: graph_page に show_remote/show_tags クエリパラメータを追加する"
```

---

### Task 3: CSS にトグルボタンスタイルを追加する

**Files:**
- Modify: `static/css/style.css`

- [ ] **Step 1: style.css にトグルボタンスタイルを追記する**

`static/css/style.css` の末尾に以下を追加する:

```css
/* リモート・タグ表示トグルボタン */
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

- [ ] **Step 2: コミットする**

```bash
git add static/css/style.css
git commit -m "feat: トグルボタンの ON/OFF スタイルを追加する"
```

---

### Task 4: graph.html テンプレートにトグルボタン UI を追加する

**Files:**
- Modify: `backend/templates/graph.html`

- [ ] **Step 1: graph.html を変更する**

`backend/templates/graph.html` を以下の差分で変更する。

変更点:
1. `<main>` に `id="graph-main"` を追加する
2. `<header>` を flex レイアウトにしてリポジトリ名（左）とトグルボタン群（右）を配置する

変更前:
```html
<main class="l--flex" style="height: 100%">
  <section class="-p:20 -ov:auto -bgc:white" aria-label="コミットグラフ"
           style="flex: 2; border-right: 1px solid var(--divider)">
    <header>
      <h1>{{ repo_name }}</h1>
    </header>
```

変更後:
```html
<main id="graph-main" class="l--flex" style="height: 100%">
  <section class="-p:20 -ov:auto -bgc:white" aria-label="コミットグラフ"
           style="flex: 2; border-right: 1px solid var(--divider)">
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
```

- [ ] **Step 2: 開発サーバーを起動して動作を手動確認する**

```bash
uv run task dev
```

ブラウザで `http://localhost:8000` を開き、リポジトリを登録してグラフ画面に遷移する。

確認項目:
1. ヘッダー右端に "Remote" と "Tag" ボタンが青で表示される
2. Remote ボタンをクリック → リモートブランチのレーンが消え URL に `show_remote=false` が入る
3. Tag ボタンをクリック → タグバッジが消え URL に `show_tags=false` が入る
4. リロードしてもトグル状態が維持される
5. 両方 OFF にしてもクラッシュしない

- [ ] **Step 3: 全テストを実行して回帰がないことを確認する**

```bash
uv run task test
```

期待: すべて PASS。

- [ ] **Step 4: lint と型チェックを実行する**

```bash
uv run task lint && uv run task typecheck
```

期待: エラーなし。

- [ ] **Step 5: コミットする**

```bash
git add backend/templates/graph.html
git commit -m "feat: グラフ画面にリモート・タグ表示トグルボタンを追加する"
```
