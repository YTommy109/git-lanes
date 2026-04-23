"""API の異常系結合テスト。"""

from fastapi.testclient import TestClient

from backend.main import app
from tests.support.git_repo_fixture import make_two_commit_repo


def test_register_rejects_plain_directory(tmp_path, monkeypatch):
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))
    plain = tmp_path / "not_git"
    plain.mkdir()
    client = TestClient(app)

    # --- Act ---
    response = client.post("/api/repos", data={"path": str(plain)})

    # --- Assert ---
    assert response.status_code == 400


def test_register_rejects_duplicate_path(tmp_path, monkeypatch):
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))
    repo_path = make_two_commit_repo(tmp_path / "repo")
    client = TestClient(app)
    first = client.post("/api/repos", data={"path": str(repo_path)}, follow_redirects=False)
    assert first.status_code == 303

    # --- Act ---
    second = client.post("/api/repos", data={"path": str(repo_path)}, follow_redirects=False)

    # --- Assert ---
    assert second.status_code == 409


def test_graph_returns_404_for_unknown_repo(tmp_path, monkeypatch):
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))
    client = TestClient(app)

    # --- Act ---
    response = client.get("/repos/00000000-0000-0000-0000-000000000000/graph")

    # --- Assert ---
    assert response.status_code == 404
