"""アプリ内自動アップデートのインストール処理。"""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Literal

from backend.services import update_service

_SCRIPT_PATH = Path("/tmp/git-lanes-updater.sh")

InstallResult = Literal["ok", "no_dmg", "mount_failed", "no_app", "not_frozen"]


def _get_app_path() -> Path | None:
    """PyInstaller 環境での .app バンドルパスを返す。

    Returns:
        .app バンドルの Path。開発環境（sys.frozen が偽）なら None。
    """
    if not getattr(sys, "frozen", False):
        return None
    # sys.executable = /Applications/Git Lanes.app/Contents/MacOS/Git Lanes
    return Path(sys.executable).parent.parent.parent


def _mount_dmg(dmg_path: str) -> Path | None:
    """DMG をマウントしてマウントポイントを返す。

    plist 出力で確実にパースする。quarantine 属性を事前に除去する。

    Args:
        dmg_path: DMG ファイルのパス。

    Returns:
        マウントポイントの Path。失敗時は None。
    """
    subprocess.run(
        ["xattr", "-d", "com.apple.quarantine", dmg_path],
        capture_output=True,
    )
    try:
        result = subprocess.run(
            ["hdiutil", "attach", dmg_path, "-nobrowse", "-agree", "-plist"],
            capture_output=True,
            check=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    try:
        plist = plistlib.loads(result.stdout)
    except Exception:
        return None
    for entity in plist.get("system-entities", []):
        if "mount-point" in entity:
            return Path(entity["mount-point"])
    return None


def _write_updater_script(app_path: Path, mount_point: Path, new_app_src: Path) -> Path:
    """インストール用シェルスクリプトを /tmp に書き出す。

    Args:
        app_path: 現在の .app パス（削除対象）。
        mount_point: DMG のマウントポイント（アンマウント対象）。
        new_app_src: DMG 内の新しい .app パス（コピー元）。

    Returns:
        書き出したスクリプトの Path。
    """
    script = (
        "#!/bin/bash\n"
        "sleep 3\n"
        f'rm -rf "{app_path}"\n'
        f'cp -R "{new_app_src}" "{app_path.parent}/"\n'
        f'hdiutil detach "{mount_point}" -quiet\n'
        f'open "{app_path}"\n'
    )
    _SCRIPT_PATH.write_text(script)
    _SCRIPT_PATH.chmod(0o755)
    return _SCRIPT_PATH


def install_update() -> InstallResult:
    """DMG をマウントして .app を差し替え、再起動スクリプトを実行する。

    Returns:
        実行結果コード。成功時は "ok"（その後 sys.exit するため返らない）。
    """
    dmg_path = update_service.get_download_state().get("dmg_path")
    if not dmg_path or not Path(dmg_path).exists():
        return "no_dmg"
    mount_point = _mount_dmg(dmg_path)
    if mount_point is None:
        return "mount_failed"
    apps = list(mount_point.glob("*.app"))
    if not apps:
        return "no_app"
    app_path = _get_app_path()
    if app_path is None:
        return "not_frozen"
    _write_updater_script(app_path, mount_point, apps[0])
    subprocess.Popen(["bash", str(_SCRIPT_PATH)])
    sys.exit(0)
