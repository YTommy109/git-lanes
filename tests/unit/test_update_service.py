"""update_service のバージョンチェック機能の単体テスト。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import backend.services.update_service as svc


def _make_github_response(tag: str, assets: list[dict] | None = None) -> MagicMock:
    """GitHub API レスポンスのモックを生成する。"""
    mock = MagicMock()
    mock.json.return_value = {"tag_name": tag, "assets": assets or []}
    mock.raise_for_status = MagicMock()
    return mock


def test_check_update_新バージョンあり():
    # --- Arrange ---
    svc._cache["checked_at"] = None
    assets = [
        {"name": "GitLanes-0.2.0.dmg", "browser_download_url": "https://example.com/test.dmg"}
    ]
    mock_resp = _make_github_response("v0.2.0", assets)

    # --- Act ---
    with patch("backend.services.update_service.httpx.get", return_value=mock_resp):
        result = svc.check_update()

    # --- Assert ---
    assert result["available"] is True
    assert result["version"] == "0.2.0"
    assert result["download_url"] == "https://example.com/test.dmg"


def test_check_update_最新バージョン():
    # --- Arrange ---
    svc._cache["checked_at"] = None
    mock_resp = _make_github_response(f"v{svc._CURRENT_VERSION}")

    # --- Act ---
    with patch("backend.services.update_service.httpx.get", return_value=mock_resp):
        result = svc.check_update()

    # --- Assert ---
    assert result["available"] is False


def test_check_update_キャッシュが効く():
    # --- Arrange ---
    svc._cache["checked_at"] = None
    mock_resp = _make_github_response("v0.2.0")

    # --- Act ---
    with patch("backend.services.update_service.httpx.get", return_value=mock_resp) as mock_get:
        svc.check_update()
        svc.check_update()  # 2回目はキャッシュから返す

    # --- Assert ---
    assert mock_get.call_count == 1
