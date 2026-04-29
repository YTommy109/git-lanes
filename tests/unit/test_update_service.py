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
        {"name": "GitLanes-999.9.9.dmg", "browser_download_url": "https://example.com/test.dmg"}
    ]
    mock_resp = _make_github_response("v999.9.9", assets)

    # --- Act ---
    with patch("backend.services.update_service.httpx.get", return_value=mock_resp):
        result = svc.check_update()

    # --- Assert ---
    assert result["available"] is True
    assert result["version"] == "999.9.9"
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


def test_download_update_進捗更新(tmp_path):
    # --- Arrange ---
    svc._download_state.update({"percent": 0, "status": "idle", "dmg_path": None})
    chunk_data = [b"a" * 50, b"b" * 50]
    dmg_dest = tmp_path / "test.dmg"

    class FakeResponse:
        headers = {"content-length": "100"}

        def raise_for_status(self) -> None:
            pass

        def iter_bytes(self, chunk_size: int | None = None):
            return iter(chunk_data)

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    # --- Act ---
    with patch("backend.services.update_service.httpx.stream", return_value=FakeResponse()):
        svc._do_download("https://example.com/test.dmg", dest=dmg_dest)

    # --- Assert ---
    assert svc._download_state["status"] == "done"
    assert svc._download_state["percent"] == 100
    assert svc._download_state["dmg_path"] == str(dmg_dest)
