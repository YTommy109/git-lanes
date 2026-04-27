"""アプリ内自動アップデート処理。"""

from __future__ import annotations

import threading
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


def get_download_state() -> dict:
    """ダウンロード状態のコピーを返す。"""
    return dict(_download_state)


def _do_download(url: str, dest: Path | None = None) -> None:
    """実際のダウンロード処理（バックグラウンドスレッドで実行）。

    Args:
        url: DMG のダウンロード URL。
        dest: 保存先パス。None のとき ~/Downloads/GitLanes-update.dmg に保存する。
    """
    _download_state.update({"percent": 0, "status": "downloading", "dmg_path": None})
    dmg_path = dest or Path.home() / "Downloads" / "GitLanes-update.dmg"
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=300) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with dmg_path.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        _download_state["percent"] = int(downloaded / total * 100)
        _download_state["status"] = "done"
        _download_state["dmg_path"] = str(dmg_path)
    except Exception:
        _download_state["status"] = "error"


def download_update(url: str) -> None:
    """ダウンロードをバックグラウンドスレッドで開始する。

    Args:
        url: DMG のダウンロード URL。
    """
    if _download_state["status"] == "downloading":
        return
    threading.Thread(target=_do_download, args=(url,), daemon=True).start()
