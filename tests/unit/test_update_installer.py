"""update_installer の単体テスト。"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import backend.services.update_installer as installer
import backend.services.update_service as svc


@pytest.fixture(autouse=True)
def reset_download_state():
    """各テスト前後にグローバルなダウンロード状態をリセットする。"""
    svc._download_state.update({"percent": 0, "status": "idle", "dmg_path": None})
    yield
    svc._download_state.update({"percent": 0, "status": "idle", "dmg_path": None})


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
    assert f'cp -R "{new_app_src}"' in content
    assert "sleep 3" in content


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


def test_mount_dmg_plistパース失敗時はNoneを返す(tmp_path):
    # --- Arrange ---
    dmg_file = tmp_path / "test.dmg"
    dmg_file.touch()
    mock_result = MagicMock()
    mock_result.stdout = b"not valid plist data"

    # --- Act ---
    with patch("subprocess.run", return_value=mock_result):
        result = installer._mount_dmg(str(dmg_file))

    # --- Assert ---
    assert result is None


def test_mount_dmg_mount_pointなしの場合はNoneを返す(tmp_path):
    # --- Arrange ---
    dmg_file = tmp_path / "test.dmg"
    dmg_file.touch()
    # mount-point キーを持たないエンティティのみの plist
    data = {"system-entities": [{"dev-entry": "/dev/disk4"}]}
    mock_result = MagicMock()
    mock_result.stdout = plistlib.dumps(data)

    # --- Act ---
    with patch("subprocess.run", return_value=mock_result):
        result = installer._mount_dmg(str(dmg_file))

    # --- Assert ---
    assert result is None


def test_install_update_appなしは_no_app_を返す(tmp_path):
    # --- Arrange ---
    dmg_file = tmp_path / "test.dmg"
    dmg_file.touch()
    svc._download_state.update({"percent": 100, "status": "done", "dmg_path": str(dmg_file)})
    plist_bytes = _make_plist_bytes("/Volumes/Test")
    mock_result = MagicMock()
    mock_result.stdout = plist_bytes

    # --- Act ---
    # glob が空リストを返す → DMG 内に .app が見つからない
    with patch("subprocess.run", return_value=mock_result):
        with patch.object(Path, "glob", return_value=[]):
            result = installer.install_update()

    # --- Assert ---
    assert result == "no_app"


def test_install_update_成功時はPopenを呼びos_exitする(tmp_path):
    # --- Arrange ---
    dmg_file = tmp_path / "test.dmg"
    dmg_file.touch()
    svc._download_state.update({"percent": 100, "status": "done", "dmg_path": str(dmg_file)})
    plist_bytes = _make_plist_bytes("/Volumes/Test")
    mock_run_result = MagicMock()
    mock_run_result.stdout = plist_bytes
    fake_exe = "/Applications/Git Lanes.app/Contents/MacOS/Git Lanes"
    script_path = tmp_path / "git-lanes-updater.sh"

    # --- Act ---
    # os._exit() はスレッドに関係なくプロセス全体を終了するため mock で差し替える
    with patch("subprocess.run", return_value=mock_run_result):
        with patch.object(Path, "glob", return_value=[Path("/Volumes/Test/Git Lanes.app")]):
            with patch.object(sys, "frozen", True, create=True):
                with patch.object(sys, "executable", fake_exe):
                    with patch.object(installer, "_SCRIPT_PATH", script_path):
                        with patch("subprocess.Popen") as mock_popen:
                            with patch("os._exit") as mock_os_exit:
                                installer.install_update()

    # --- Assert ---
    mock_os_exit.assert_called_once_with(0)
    mock_popen.assert_called_once_with(["bash", str(script_path)])
