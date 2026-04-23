"""グラフ画面の E2E スモーク。"""

from pathlib import Path

from playwright.sync_api import Page

from tests.support.git_repo_fixture import make_two_commit_repo


def test_登録後にグラフにコミットノードが表示される(page: Page, base_url: str, tmp_path: Path):
    # Given: コミットが 2 つある Git リポジトリ
    repo_path = make_two_commit_repo(tmp_path / "e2e-repo")

    # When: リポジトリを登録する
    response = page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})

    # Then: グラフにコミットノードが含まれる
    assert response.ok
    body = response.text()
    assert "commit-node" in body
