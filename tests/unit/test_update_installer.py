"""update_installer の単体テスト。"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import backend.services.update_installer as installer
import backend.services.update_service as svc


def test_get_app_path_frozen環境():
    # --- Arrange ---
    fake_exe = "/Applications/Git Lanes.app/Contents/MacOS/Git Lanes"

    # --- Act ---
    with patch.object(sys, "frozen", True, create=True):
        with patch.object(sys, "executable", fake_exe):
            result = installer._get_app_path()

    # --- Assert ---
    assert result == Path("/Applications/Git Lanes.app")


def test_get_app_path_開発環境():
    # --- Arrange / Act ---
    with patch.object(sys, "frozen", False, create=True):
        result = installer._get_app_path()

    # --- Assert ---
    assert result is None


def test_write_updater_script_内容検証(tmp_path):
    # --- Arrange ---
    app_path = Path("/Applications/Git Lanes.app")
    mount_point = Path("/Volumes/Git Lanes")
    new_app_src = Path("/Volumes/Git Lanes/Git Lanes.app")
    script_path = tmp_path / "git-lanes-updater.sh"

    # --- Act ---
    with patch.object(installer, "_SCRIPT_PATH", script_path):
        result = installer._write_updater_script(app_path, mount_point, new_app_src)

    # --- Assert ---
    content = result.read_text()
    assert "hdiutil detach" in content
    assert f'open "{app_path}"' in content
    assert str(app_path) in content


def _make_plist_bytes(mount_point: str) -> bytes:
    """テスト用 hdiutil plist 出力を生成する。"""
    data = {
        "system-entities": [
            {"dev-entry": "/dev/disk4"},
            {"dev-entry": "/dev/disk4s1", "content-hint": "Apple_partition_map"},
            {
                "dev-entry": "/dev/disk4s2",
                "content-hint": "Apple_HFS",
                "mount-point": mount_point,
            },
        ]
    }
    return plistlib.dumps(data)


def test_mount_dmg_plist_パースで正しいマウントポイントを返す(tmp_path):
    # --- Arrange ---
    dmg_file = tmp_path / "test.dmg"
    dmg_file.touch()
    mock_result = MagicMock()
    mock_result.stdout = _make_plist_bytes("/Volumes/Git Lanes")

    # --- Act ---
    with patch("subprocess.run", return_value=mock_result):
        result = installer._mount_dmg(str(dmg_file))

    # --- Assert ---
    assert result == Path("/Volumes/Git Lanes")


def test_mount_dmg_hdiutil失敗時はNoneを返す(tmp_path):
    # --- Arrange ---
    import subprocess

    dmg_file = tmp_path / "test.dmg"
    dmg_file.touch()
    error = subprocess.CalledProcessError(1, "hdiutil")

    # --- Act ---
    with patch("subprocess.run", side_effect=[MagicMock(), error]):
        result = installer._mount_dmg(str(dmg_file))

    # --- Assert ---
    assert result is None


def test_install_update_開発環境では_not_frozen_を返す(tmp_path):
    # --- Arrange ---
    dmg_file = tmp_path / "test.dmg"
    dmg_file.touch()
    svc._download_state.update({"percent": 100, "status": "done", "dmg_path": str(dmg_file)})
    plist_bytes = _make_plist_bytes("/Volumes/Test")
    mock_result = MagicMock()
    mock_result.stdout = plist_bytes

    # --- Act ---
    with patch.object(sys, "frozen", False, create=True):
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "glob", return_value=[Path("/Volumes/Test/App.app")]):
                result = installer.install_update()

    # --- Assert ---
    assert result == "not_frozen"


def test_install_update_dmgなしは_no_dmg_を返す():
    # --- Arrange ---
    svc._download_state.update({"percent": 0, "status": "idle", "dmg_path": None})

    # --- Act ---
    result = installer.install_update()

    # --- Assert ---
    assert result == "no_dmg"


def test_install_update_マウント失敗は_mount_failed_を返す(tmp_path):
    # --- Arrange ---
    import subprocess

    dmg_file = tmp_path / "test.dmg"
    dmg_file.touch()
    svc._download_state.update({"percent": 100, "status": "done", "dmg_path": str(dmg_file)})
    error = subprocess.CalledProcessError(1, "hdiutil")

    # --- Act ---
    with patch("subprocess.run", side_effect=[MagicMock(), error]):
        result = installer.install_update()

    # --- Assert ---
    assert result == "mount_failed"
