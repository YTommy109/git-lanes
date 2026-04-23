from playwright.sync_api import Page


def test_ヘルスチェックエンドポイントが応答する(page: Page, base_url: str):
    # Given: アプリが起動している（conftest の _server fixture が保証）
    # When: ヘルスチェックエンドポイントにリクエストする
    response = page.request.get(f"{base_url}/health")

    # Then: 200 と {"status": "ok"} が返る
    assert response.status == 200
    assert response.json()["status"] == "ok"
