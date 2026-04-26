"""グラフ画面の E2E スモーク。"""

from pathlib import Path

from playwright.sync_api import Page

from tests.support.git_repo_fixture import make_two_branch_repo, make_two_commit_repo


def test_登録後にグラフにコミットノードが表示される(page: Page, base_url: str, tmp_path: Path):
    # Given: コミットが 2 つある Git リポジトリ
    repo_path = make_two_commit_repo(tmp_path / "e2e-repo")

    # When: リポジトリを登録する
    response = page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})

    # Then: グラフにコミットノードが含まれる
    assert response.ok
    body = response.text()
    assert "commit-node" in body


def test_マルチブランチリポジトリでグラフにコミットノードが表示される(
    page: Page, base_url: str, tmp_path: Path
):
    # Given: main と feat ブランチを持つリポジトリ
    repo_path = make_two_branch_repo(tmp_path / "e2e-multi-repo")

    # When: リポジトリを登録する
    response = page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})

    # Then: グラフに複数のコミットノードが含まれる
    assert response.ok
    body = response.text()
    assert body.count("commit-node") >= 3
