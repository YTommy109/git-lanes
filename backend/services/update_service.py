"""アプリ内自動アップデート処理。"""

from __future__ import annotations

import time
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path

import httpx

GITHUB_API_URL = "https://api.github.com/repos/YTommy109/git-lanes/releases/latest"
_CACHE_TTL = 3600
_SCRIPT_PATH = Path("/tmp/git-lanes-updater.sh")

try:
    _CURRENT_VERSION = _pkg_version("git-lanes")
except PackageNotFoundError:
    _CURRENT_VERSION = "0.0.0"

_cache: dict = {"checked_at": None, "result": None}
_download_state: dict = {"percent": 0, "status": "idle", "dmg_path": None}


def _is_newer(remote: str, current: str) -> bool:
    """リモートバージョンが現在より新しいかを比較する。"""

    def to_tuple(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split("."))

    return to_tuple(remote) > to_tuple(current)


def _find_dmg_url(assets: list[dict]) -> str | None:
    """リリースアセットから DMG のダウンロード URL を取得する。"""
    for asset in assets:
        if asset.get("name", "").endswith(".dmg"):
            return asset.get("browser_download_url")
    return None


def check_update() -> dict:
    """GitHub Releases API で最新バージョンを確認する（1時間TTLキャッシュ）。

    Returns:
        available: 更新があれば True。version: 最新バージョン文字列。
        download_url: DMG のダウンロード URL（なければ None）。
    """
    now = time.monotonic()
    if _cache["checked_at"] and now - _cache["checked_at"] < _CACHE_TTL:
        return _cache["result"]
    try:
        resp = httpx.get(GITHUB_API_URL, timeout=5, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        tag = data["tag_name"].lstrip("v")
        result: dict = {
            "available": _is_newer(tag, _CURRENT_VERSION),
            "version": tag,
            "download_url": _find_dmg_url(data.get("assets", [])),
        }
    except Exception:
        result = {"available": False, "version": _CURRENT_VERSION, "download_url": None}
    _cache["checked_at"] = now
    _cache["result"] = result
    return result
