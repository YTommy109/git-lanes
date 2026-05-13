"""app.py のウィンドウ状態関連ユーティリティのテスト。"""

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
