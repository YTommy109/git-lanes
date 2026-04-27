"""アプリ内自動アップデートのインストール処理。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.services import update_service

_SCRIPT_PATH = Path("/tmp/git-lanes-updater.sh")


def _get_app_path() -> Path | None:
    """PyInstaller 環境での .app バンドルパスを返す。

    Returns:
        .app バンドルの Path。開発環境（sys.frozen が偽）なら None。
    """
    if not getattr(sys, "frozen", False):
        return None
    # sys.executable = /Applications/Git Lanes.app/Contents/MacOS/Git Lanes
    return Path(sys.executable).parent.parent.parent


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


def install_update() -> None:
    """DMG をマウントして .app を差し替え、再起動スクリプトを実行する。

    開発環境（sys.frozen が偽）では何もせず return する。
    ダウンロードが完了していない場合も何もせず return する。
    """
    dmg_path = update_service.get_download_state().get("dmg_path")
    if not dmg_path or not Path(dmg_path).exists():
        return
    try:
        result = subprocess.run(
            ["hdiutil", "attach", dmg_path, "-nobrowse", "-agree"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return
    last_line = result.stdout.strip().split("\n")[-1]
    mount_point = Path(last_line.split("\t")[-1].strip())
    apps = list(mount_point.glob("*.app"))
    if not apps:
        return
    app_path = _get_app_path()
    if app_path is None:
        return
    script_path = _write_updater_script(app_path, mount_point, apps[0])
    subprocess.Popen(["bash", str(script_path)])
    sys.exit(0)
