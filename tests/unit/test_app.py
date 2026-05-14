from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_ヘルスチェックが200を返す():
    # --- Act ---
    response = client.get("/health")

    # --- Assert ---
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_check_update_更新なし時に_update_banner_idを持つdivを返す():
    # --- Arrange ---
    import backend.services.update_service as svc

    svc._cache["checked_at"] = None
    client = TestClient(app)

    # --- Act ---
    with patch("backend.services.update_service.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": f"v{svc._CURRENT_VERSION}",
            "assets": [],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        response = client.get("/api/update/check")

    # --- Assert ---
    assert response.status_code == 200
    assert 'id="update-banner"' in response.text


def test_update_dialog_最新状態のとき200を返す():
    # --- Arrange ---
    import backend.services.update_service as svc

    svc._cache["checked_at"] = None
    client = TestClient(app)

    # --- Act ---
    with patch("backend.services.update_service.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": f"v{svc._CURRENT_VERSION}",
            "assets": [],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        response = client.get("/api/update/dialog")

    # --- Assert ---
    assert response.status_code == 200
    assert "最新バージョンです" in response.text


def test_update_dialog_更新ありのとき200を返す():
    # --- Arrange ---
    import backend.services.update_service as svc

    svc._cache["checked_at"] = None
    client = TestClient(app)

    # --- Act ---
    with patch("backend.services.update_service.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": "v999.0.0",
            "assets": [
                {
                    "name": "GitLanes-999.0.0.dmg",
                    "browser_download_url": "https://example.com/test.dmg",
                }
            ],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        response = client.get("/api/update/dialog")

    # --- Assert ---
    assert response.status_code == 200
    assert "999.0.0" in response.text
    assert "ダウンロード" in response.text
