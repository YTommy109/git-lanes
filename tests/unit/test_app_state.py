"""app.py のウィンドウ状態関連ユーティリティのテスト。"""

import json
from unittest.mock import MagicMock

from backend.app import _build_initial_url
from backend.state_store import WindowState


def test_build_initial_url_はリポジトリ未保存のときルートを返す():
    """repo_id が None のとき / を返す。"""
    # --- Arrange ---
    state = WindowState()

    # --- Act ---
    result = _build_initial_url(8000, state)

    # --- Assert ---
    assert result == "http://127.0.0.1:8000/"


def test_build_initial_url_はリポジトリ保存済みのときグラフ画面を返す():
    """repo_id が設定されているときグラフ画面 URL を返す。"""
    # --- Arrange ---
    state = WindowState(repo_id="abc-123", show_remote=True, show_tags=False)

    # --- Act ---
    result = _build_initial_url(8000, state)

    # --- Assert ---
    assert "/repos/abc-123/graph" in result
    assert "show_tags=false" in result


def test_build_initial_url_はコミットハッシュを含める():
    """commit_hash が設定されているとき active_commit パラメータを含める。"""
    # --- Arrange ---
    h = "a" * 40
    state = WindowState(repo_id="abc-123", commit_hash=h)

    # --- Act ---
    result = _build_initial_url(8000, state)

    # --- Assert ---
    assert f"active_commit={h}" in result


def test_main_は終了時にウィンドウ状態をファイルに保存する(tmp_path, monkeypatch):
    """webview.start() が返った後にウィンドウ状態がファイルに書き込まれること。

    終了直前の debounce タイマーがデーモンスレッドで強制終了されても
    状態が失われないことを保証する。
    """
    # --- Arrange ---
    import backend.app as app_module

    state = WindowState(x=100, y=200, width=1024, height=768)
    path = tmp_path / "window_state.json"

    monkeypatch.setattr(app_module, "_save_timer", None)
    monkeypatch.setattr("backend.app.webview.create_window", lambda *a, **kw: MagicMock())
    monkeypatch.setattr("backend.app.webview.start", lambda **kw: None)
    monkeypatch.setattr("backend.app.Menu", MagicMock())
    monkeypatch.setattr("backend.app.MenuAction", MagicMock())
    monkeypatch.setattr("backend.app.state_store.load", lambda p: state)
    monkeypatch.setattr("backend.app.paths.window_state_path", lambda: path)
    monkeypatch.setattr("backend.app._find_free_port", lambda: 8999)
    monkeypatch.setattr("backend.app._start_server", lambda port: None)
    monkeypatch.setattr("backend.app._wait_for_server", lambda *a, **kw: True)

    # --- Act ---
    app_module.main()

    # --- Assert ---
    assert path.exists(), "ウィンドウ状態ファイルが作成されていない"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["x"] == 100
    assert data["y"] == 200
    assert data["width"] == 1024
