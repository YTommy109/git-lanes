"""update_window の単体テスト。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_open_update_dialog_すでに開いていれば2重起動しない():
    # --- Arrange ---
    import backend.update_window as uw

    uw._update_win = MagicMock()  # 開いている状態を模擬

    # --- Act ---
    with patch("backend.update_window.webview.create_window") as mock_create:
        uw.open_update_dialog(8000)

    # --- Assert ---
    mock_create.assert_not_called()

    # テスト後にグローバルをリセットする
    uw._update_win = None
