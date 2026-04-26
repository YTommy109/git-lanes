# 登録済みリポジトリのサイドバー表示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 登録済みリポジトリを常設サイドバーに一覧表示し、クリックで即座に切り替えられるようにする。

**Architecture:** `base.html` に左サイドバーを追加し、全画面（ウェルカム・グラフ）で共通表示する。リポジトリ一覧は Jinja2 でサーバーサイドレンダリングし、JavaScript は使用しない。各ルートで `list_repositories()` を呼び出しテンプレートコンテキストに渡す。

**Tech Stack:** Python / FastAPI / SQLModel / Jinja2 / htmx / hyperscript / LismCSS

---

## ファイル一覧

| ファイル | 種別 | 担当 |
|---------|------|------|
| `backend/repositories/cache_repo.py` | 修正 | `list_repositories()` 関数を追加 |
| `backend/routers/html.py` | 修正 | 全ルートに `repos`・`current_repo_id` コンテキストを追加 |
| `backend/templates/base.html` | 修正 | サイドバー HTML（リスト＋フォーム）を追加 |
| `backend/templates/welcome.html` | 修正 | フォームを削除し説明テキストのみにする |
| `static/css/style.css` | 修正 | サイドバーのアクティブリンクスタイルを追加 |
| `tests/unit/test_cache_repo.py` | 修正 | `list_repositories` の単体テストを追加 |
| `tests/e2e/test_sidebar.py` | 新規 | サイドバーの E2E テストを追加 |

---

## Task 1: `list_repositories` の単体テストと実装

**Files:**
- Modify: `tests/unit/test_cache_repo.py`
- Modify: `backend/repositories/cache_repo.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unit/test_cache_repo.py` の末尾に追加する（`test_list_branches_ブランチなしは空リスト` の後）：

```python
# ── list_repositories ──────────────────────────────────────


def test_list_repositories_複数件をname昇順で返す(session):
    # --- Arrange ---
    cache_repo.insert_repository(session, "r2", "/path/r2", "zeta")
    cache_repo.insert_repository(session, "r1", "/path/r1", "alpha")

    # --- Act ---
    result = cache_repo.list_repositories(session)

    # --- Assert ---
    assert [r.name for r in result] == ["alpha", "zeta"]


def test_list_repositories_0件は空リストを返す(session):
    # --- Act ---
    result = cache_repo.list_repositories(session)

    # --- Assert ---
    assert result == []
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
uv run pytest tests/unit/test_cache_repo.py::test_list_repositories_複数件をname昇順で返す tests/unit/test_cache_repo.py::test_list_repositories_0件は空リストを返す -v
```

期待: `AttributeError: module 'backend.repositories.cache_repo' has no attribute 'list_repositories'` で失敗

- [ ] **Step 3: 実装を追加する**

`backend/repositories/cache_repo.py` の `get_repository_by_path` 関数の直前（99行目付近）に追加する：

```python
def list_repositories(session: Session) -> list[Repository]:
    """登録済みリポジトリを name 昇順で全件返す。

    Args:
        session: DB セッション。

    Returns:
        Repository のリスト。0 件のときは空リスト。
    """
    return list(session.exec(select(Repository).order_by(Repository.name)).all())
```

- [ ] **Step 4: テストを実行して成功を確認する**

```bash
uv run pytest tests/unit/test_cache_repo.py::test_list_repositories_複数件をname昇順で返す tests/unit/test_cache_repo.py::test_list_repositories_0件は空リストを返す -v
```

期待: 2 件 PASSED

- [ ] **Step 5: 既存テストも全件パスを確認する**

```bash
uv run pytest tests/unit/test_cache_repo.py -v
```

期待: 全件 PASSED

- [ ] **Step 6: コミットする**

```bash
git add backend/repositories/cache_repo.py tests/unit/test_cache_repo.py
git commit -m "feat: list_repositories 関数を追加する"
```

---

## Task 2: HTML ルートに `repos` コンテキストを追加する

**Files:**
- Modify: `backend/routers/html.py`

- [ ] **Step 1: `welcome` 関数を更新する**

`backend/routers/html.py` の `welcome` 関数（26〜28行目）を以下に置き換える：

```python
@router.get("/", response_class=HTMLResponse)
async def welcome(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ウェルカム画面を返す。"""
    repos = cache_repo.list_repositories(session)
    return templates.TemplateResponse(
        request, "welcome.html", {"repos": repos, "current_repo_id": None}
    )
```

- [ ] **Step 2: `graph_page` 関数に `repos` コンテキストを追加する**

`backend/routers/html.py` の `graph_page` 関数の末尾（88〜89行目）を以下に置き換える：

```python
    nodes, edges, branch_lanes = graph_layout.build_multi_lane_layout(rows, parents, branches)
    context = _build_graph_context(rid, rec, nodes, edges, branch_lanes)
    context["repos"] = cache_repo.list_repositories(session)
    context["current_repo_id"] = rid
    return templates.TemplateResponse(request, "graph.html", context)
```

- [ ] **Step 3: 既存のルートテストが通るか確認する**

```bash
uv run pytest tests/unit/test_app.py -v
```

期待: 全件 PASSED

- [ ] **Step 4: コミットする**

```bash
git add backend/routers/html.py
git commit -m "feat: 全ルートにリポジトリ一覧コンテキストを追加する"
```

---

## Task 3: `base.html` にサイドバーを追加する

**Files:**
- Modify: `backend/templates/base.html`
- Modify: `static/css/style.css`

- [ ] **Step 1: `style.css` にサイドバーのアクティブリンクスタイルを追加する**

`static/css/style.css` の末尾に追加する：

```css
/* サイドバーリポジトリリンク */
.repo-link {
  display: block;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  text-decoration: none;
  color: inherit;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.repo-link:hover {
  background: var(--base-3);
}

.repo-link.is-active {
  background: var(--blue);
  color: white;
}
```

- [ ] **Step 2: `base.html` をサイドバーレイアウトに更新する**

`backend/templates/base.html` を以下で全置換する：

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8"/>
  <title>{% block title %}Git Lanes{% endblock %}</title>
  <link href="https://cdn.jsdelivr.net/npm/lism-css@0.16.0/dist/css/main.css" rel="stylesheet"/>
  <link rel="stylesheet" href="/static/css/style.css"/>
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <script src="https://unpkg.com/hyperscript.org@0.9.14"></script>
</head>
<body>
<div class="l--flex" style="min-height: 100vh">
  <nav aria-label="リポジトリ一覧"
       style="width: 220px; min-height: 100vh; flex-shrink: 0; border-right: 1px solid var(--divider);
              display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; background: var(--base-2)">
    <p class="-fw:bold -fz:s -c:text-2" style="margin: 0">リポジトリ</p>
    <ul style="list-style: none; padding: 0; margin: 0; flex: 1; display: flex; flex-direction: column; gap: 0.2rem">
      {% for repo in repos %}
      <li>
        <a href="/repos/{{ repo.id }}/graph"
           class="repo-link{% if repo.id == current_repo_id %} is-active{% endif %}"
           title="{{ repo.name }}">{{ repo.name }}</a>
      </li>
      {% endfor %}
    </ul>
    <form method="post" action="/api/repos" class="l--stack -g:8"
          _="on submit toggle @disabled on <button/>">
      <label class="l--stack -g:4" style="font-size: 0.8rem">
        パスを追加
        <input name="path" type="text" required autocomplete="off"
               placeholder="/path/to/repo"
               style="width: 100%; padding: 0.3rem 0.4rem; font-size: 0.8rem"/>
      </label>
      <button type="submit" style="font-size: 0.8rem">追加</button>
    </form>
  </nav>
  <div style="flex: 1; min-width: 0">
    {% block body %}{% endblock %}
  </div>
</div>
</body>
</html>
```

- [ ] **Step 3: 開発サーバーを起動して目視確認する**

```bash
uv run task dev
```

ブラウザで `http://localhost:8000` を開き、左サイドバーが表示されていることを確認する。

- [ ] **Step 4: コミットする**

```bash
git add backend/templates/base.html static/css/style.css
git commit -m "feat: base.html にサイドバーレイアウトを追加する"
```

---

## Task 4: `welcome.html` からフォームを削除する

**Files:**
- Modify: `backend/templates/welcome.html`

- [ ] **Step 1: `welcome.html` をフォームなしの説明画面に更新する**

`backend/templates/welcome.html` を以下で全置換する：

```html
{% extends "base.html" %}
{% block title %}Git Lanes — ようこそ{% endblock %}
{% block body %}
<main class="l--stack -p:40" style="max-width: 30rem; margin: 3rem auto">
  <h1>Git Lanes</h1>
  <p class="-c:text-2">左のサイドバーからリポジトリを追加・選択してください。</p>
</main>
{% endblock %}
```

- [ ] **Step 2: 開発サーバーで目視確認する**

ブラウザで `http://localhost:8000` を開き、以下を確認する：
- ウェルカム画面に説明テキストのみ表示される
- フォームはサイドバーに表示される

- [ ] **Step 3: コミットする**

```bash
git add backend/templates/welcome.html
git commit -m "feat: ウェルカム画面のフォームをサイドバーに委譲する"
```

---

## Task 5: サイドバーの E2E テストを追加する

**Files:**
- Create: `tests/e2e/test_sidebar.py`

- [ ] **Step 1: テストファイルを作成する**

`tests/e2e/test_sidebar.py` を新規作成する：

```python
"""サイドバーのリポジトリ一覧 E2E テスト。"""

from pathlib import Path

from playwright.sync_api import Page

from tests.support.git_repo_fixture import make_two_commit_repo


def test_登録済みリポジトリがウェルカム画面のサイドバーに表示される(
    page: Page, base_url: str, tmp_path: Path
):
    # Given: コミットが 2 つある Git リポジトリを登録済み
    repo_path = make_two_commit_repo(tmp_path / "sidebar-welcome-repo")
    page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})

    # When: ウェルカム画面を開く
    page.goto(base_url)

    # Then: サイドバーにリポジトリ名が表示される
    sidebar = page.locator('[aria-label="リポジトリ一覧"]')
    assert sidebar.locator(f"text={repo_path.name}").is_visible()


def test_サイドバーのリポジトリ名クリックでグラフ画面に遷移する(
    page: Page, base_url: str, tmp_path: Path
):
    # Given: リポジトリを登録してウェルカム画面を表示
    repo_path = make_two_commit_repo(tmp_path / "sidebar-nav-repo")
    page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})
    page.goto(base_url)

    # When: サイドバーのリポジトリ名をクリックする
    sidebar = page.locator('[aria-label="リポジトリ一覧"]')
    sidebar.locator(f"text={repo_path.name}").click()
    page.wait_for_selector(".commit-node")

    # Then: グラフ画面に遷移してコミットノードが表示される
    assert "graph" in page.url


def test_グラフ画面で現在のリポジトリがハイライトされる(
    page: Page, base_url: str, tmp_path: Path
):
    # Given: リポジトリを登録してグラフ画面を表示
    repo_path = make_two_commit_repo(tmp_path / "sidebar-active-repo")
    response = page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})
    page.goto(response.url)
    page.wait_for_selector(".commit-node")

    # When: サイドバーを確認する
    sidebar = page.locator('[aria-label="リポジトリ一覧"]')
    active_link = sidebar.locator(".repo-link.is-active")

    # Then: 現在のリポジトリリンクがハイライトされている
    assert active_link.text_content().strip() == repo_path.name


def test_サイドバーのフォームから新規登録するとサイドバーに追加される(
    page: Page, base_url: str, tmp_path: Path
):
    # Given: ウェルカム画面を表示
    repo_path = make_two_commit_repo(tmp_path / "sidebar-add-repo")
    page.goto(base_url)

    # When: サイドバーのフォームにパスを入力して送信する
    sidebar = page.locator('[aria-label="リポジトリ一覧"]')
    sidebar.locator('input[name="path"]').fill(str(repo_path))
    sidebar.locator('button[type="submit"]').click()
    page.wait_for_selector(".commit-node")

    # Then: グラフ画面に遷移し、サイドバーにリポジトリが追加されている
    assert "graph" in page.url
    sidebar = page.locator('[aria-label="リポジトリ一覧"]')
    assert sidebar.locator(f"text={repo_path.name}").is_visible()
```

- [ ] **Step 2: E2E テストを実行して成功を確認する**

```bash
uv run task test:e2e -- tests/e2e/test_sidebar.py -v
```

期待: 4 件 PASSED

- [ ] **Step 3: 全テストスイートを実行する**

```bash
uv run task test
uv run task test:e2e
```

期待: 全件 PASSED

- [ ] **Step 4: lint・型チェックを実行する**

```bash
uv run task lint && uv run task typecheck
```

期待: エラーなし

- [ ] **Step 5: コミットする**

```bash
git add tests/e2e/test_sidebar.py
git commit -m "test: サイドバーの E2E テストを追加する"
```
