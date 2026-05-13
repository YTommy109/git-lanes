"""state_store の単体テスト。"""

import json

from backend.state_store import WindowState, load, save, update


def test_load_はファイル不在のときデフォルト値を返す(tmp_path):
    """ファイルが存在しない場合は WindowState のデフォルト値を返す。"""
    # --- Arrange ---
    path = tmp_path / "window_state.json"

    # --- Act ---
    result = load(path)

    # --- Assert ---
    assert isinstance(result, WindowState)
    assert result.width == 1280
    assert result.height == 800
    assert result.x is None
    assert result.repo_id is None


def test_load_は壊れた_json_のときデフォルト値を返す(tmp_path):
    """JSON が壊れている場合は WindowState のデフォルト値を返す。"""
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    path.write_text("not valid json", encoding="utf-8")

    # --- Act ---
    result = load(path)

    # --- Assert ---
    assert isinstance(result, WindowState)
    assert result.width == 1280


def test_load_は保存済みの値を返す(tmp_path):
    """保存済みの JSON から値を復元する。"""
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    path.write_text(
        json.dumps({"x": 100, "y": 200, "width": 1400, "height": 900}),
        encoding="utf-8",
    )

    # --- Act ---
    result = load(path)

    # --- Assert ---
    assert result.x == 100
    assert result.y == 200
    assert result.width == 1400
    assert result.height == 900


def test_save_は_json_ファイルに書き込む(tmp_path):
    """save() が JSON ファイルに正しく書き込む。"""
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    state = WindowState(x=10, y=20, width=800, height=600)

    # --- Act ---
    save(path, state)

    # --- Assert ---
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["x"] == 10
    assert data["width"] == 800


def test_round_trip_で値が一致する(tmp_path):
    """save() → load() でラウンドトリップしても値が一致する。"""
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    original = WindowState(
        x=50,
        y=60,
        width=1920,
        height=1080,
        repo_id="abc",
        commit_hash="a" * 40,
        show_remote=False,
        show_tags=True,
    )

    # --- Act ---
    save(path, original)
    restored = load(path)

    # --- Assert ---
    assert restored.x == 50
    assert restored.width == 1920
    assert restored.repo_id == "abc"
    assert restored.commit_hash == "a" * 40
    assert restored.show_remote is False


def test_update_は指定フィールドのみ上書きする(tmp_path):
    """update() は指定フィールドだけ変更し、他は維持する。"""
    # --- Arrange ---
    path = tmp_path / "window_state.json"
    initial = WindowState(x=10, y=20, width=1280, height=800, repo_id="old")
    save(path, initial)

    # --- Act ---
    update(path, repo_id="new", show_remote=False)

    # --- Assert ---
    result = load(path)
    assert result.repo_id == "new"
    assert result.show_remote is False
    assert result.x == 10  # 変更していないフィールドは保たれる
    assert result.width == 1280
