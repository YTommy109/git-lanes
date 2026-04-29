# tests/unit/test_paths.py
"""paths モジュールの単体テスト。"""

from backend.paths import data_dir


def test_data_dir_環境変数でオーバーライドされる(tmp_path, monkeypatch):
    """GIT_LANES_DATA_DIR が設定されているときその値を返す（paths.py line 18）。"""
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))

    # --- Act ---
    result = data_dir()

    # --- Assert ---
    assert result == tmp_path.resolve()
