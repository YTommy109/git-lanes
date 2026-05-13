# tests/unit/test_paths.py
"""paths モジュールの単体テスト。"""

from backend.paths import data_dir, window_state_path


def test_data_dir_環境変数でオーバーライドされる(tmp_path, monkeypatch):
    """GIT_LANES_DATA_DIR が設定されているときその値を返す（paths.py line 18）。"""
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))

    # --- Act ---
    result = data_dir()

    # --- Assert ---
    assert result == tmp_path.resolve()


def test_window_state_path_は_data_dir_配下を返す(tmp_path, monkeypatch):
    """window_state_path() が data_dir() 配下に window_state.json を返す。"""
    # --- Arrange ---
    monkeypatch.setenv("GIT_LANES_DATA_DIR", str(tmp_path))

    # --- Act ---
    result = window_state_path()

    # --- Assert ---
    assert result == tmp_path.resolve() / "window_state.json"
