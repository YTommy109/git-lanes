from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_ヘルスチェックが200を返す():
    # --- Act ---
    response = client.get("/health")

    # --- Assert ---
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
