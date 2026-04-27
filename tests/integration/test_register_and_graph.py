"""登録からグラフ表示までの結合テスト。"""

from fastapi.testclient import TestClient

from tests.support.git_repo_fixture import make_two_commit_repo


def test_register_redirects_and_graph_renders(tmp_path, client: TestClient):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")

    # --- Act ---
    response = client.post("/api/repos", data={"path": str(repo_path)}, follow_redirects=False)

    # --- Assert ---
    assert response.status_code == 303
    location = response.headers["location"]
    page = client.get(location)
    assert page.status_code == 200
    # class="commit-node" が 2 ノード分存在することを確認する
    assert page.text.count('class="commit-node"') == 2
