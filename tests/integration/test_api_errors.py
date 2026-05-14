"""API の異常系結合テスト。"""

from fastapi.testclient import TestClient

from tests.support.git_repo_fixture import make_two_commit_repo


def test_register_rejects_plain_directory(tmp_path, client: TestClient):
    # --- Arrange ---
    plain = tmp_path / "not_git"
    plain.mkdir()

    # --- Act ---
    response = client.post("/api/repos", data={"path": str(plain)})

    # --- Assert ---
    assert response.status_code == 400


def test_register_rejects_duplicate_path(tmp_path, client: TestClient):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    first = client.post("/api/repos", data={"path": str(repo_path)}, follow_redirects=False)
    assert first.status_code == 303

    # --- Act ---
    second = client.post("/api/repos", data={"path": str(repo_path)}, follow_redirects=False)

    # --- Assert: 既存リポジトリのグラフへリダイレクトする ---
    assert second.status_code == 303
    assert "/graph" in second.headers["location"]


def test_graph_redirects_to_welcome_for_unknown_repo(client: TestClient):
    """存在しない repo_id でグラフを開くとウェルカム画面へリダイレクトすること。

    window_state.json に古い repo_id が残っていてもエラー画面にならないために必要。
    """
    # --- Act ---
    response = client.get(
        "/repos/00000000-0000-0000-0000-000000000000/graph",
        follow_redirects=False,
    )

    # --- Assert ---
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_error_response_content_type_includes_charset_utf8(client: TestClient):
    """エラーレスポンスの Content-Type に charset=utf-8 が含まれること。

    WKWebView が文字コードを誤認識して日本語が文字化けしないために必要。
    """
    # --- Act ---
    response = client.post("/api/repos", data={"path": "/nonexistent/path/zzz"})

    # --- Assert ---
    assert response.status_code == 400
    assert "charset=utf-8" in response.headers["content-type"].lower()
