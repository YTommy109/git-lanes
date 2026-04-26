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


def test_グラフ画面で現在のリポジトリがハイライトされる(page: Page, base_url: str, tmp_path: Path):
    # Given: リポジトリを登録してグラフ画面を表示
    repo_path = make_two_commit_repo(tmp_path / "sidebar-active-repo")
    response = page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})
    page.goto(response.url)
    page.wait_for_selector(".commit-node")

    # When: サイドバーを確認する
    sidebar = page.locator('[aria-label="リポジトリ一覧"]')
    active_link = sidebar.locator(".repo-link.is-active")

    # Then: 現在のリポジトリリンクがハイライトされている
    text = active_link.text_content() or ""
    assert text.strip() == repo_path.name


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
