"""update_installer の単体テスト。"""

from __future__ import annotations

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


def test_install_update_開発環境ではスキップ(tmp_path):
    # --- Arrange ---
    svc._download_state.update(
        {"percent": 100, "status": "done", "dmg_path": str(tmp_path / "test.dmg")}
    )
    mock_run_result = MagicMock()
    mock_run_result.stdout = "/dev/disk4\tApple_HFS\t/Volumes/Test\n"

    # --- Act ---
    # _get_app_path() が None を返す（開発環境）ので sys.exit は呼ばれない
    with patch.object(sys, "frozen", False, create=True):
        with patch("subprocess.run", return_value=mock_run_result):
            with patch.object(Path, "glob", return_value=[Path("/Volumes/Test/App.app")]):
                installer.install_update()  # sys.exit(0) を呼ばずに return する

    # --- Assert ---
    # 例外なく完了していれば OK
