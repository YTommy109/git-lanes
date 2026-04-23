from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_ヘルスチェックが200を返す():
    # --- Arrange ---
    # TestClient は ASGI アプリを受け取り同期的に動作する

    # --- Act ---
    response = client.get("/health")

    # --- Assert ---
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
