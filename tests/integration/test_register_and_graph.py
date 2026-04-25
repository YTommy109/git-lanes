"""登録からグラフ表示までの結合テスト。"""

from fastapi.testclient import TestClient

from backend.main import app
from tests.support.git_repo_fixture import make_two_commit_repo


def test_register_redirects_and_graph_renders(tmp_path, monkeypatch):
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))
    repo_path = make_two_commit_repo(tmp_path / "repo")
    client = TestClient(app)

    # --- Act ---
    response = client.post("/api/repos", data={"path": str(repo_path)}, follow_redirects=False)

    # --- Assert ---
    assert response.status_code == 303
    location = response.headers["location"]
    page = client.get(location)
    assert page.status_code == 200
    assert page.text.count("commit-node") == 2
