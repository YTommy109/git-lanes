"""jinja.py のカスタムフィルターのテスト。"""

from datetime import timezone
from zoneinfo import ZoneInfo

import pytest

from backend.jinja import _resolve_tz, format_unix_timestamp


class TestFormatUnixTimestamp:
    def test_TZ環境変数が有効なタイムゾーンを参照する(self, monkeypatch: pytest.MonkeyPatch):
        # --- Arrange ---
        monkeypatch.setenv("TZ", "Asia/Tokyo")
        ts = 0  # UTC では 1970-01-01 00:00:00 → JST では 1970-01-01 09:00:00

        # --- Act ---
        result = format_unix_timestamp(ts)

        # --- Assert ---
        assert result == "1970-01-01 09:00:00 JST"

    def test_TZ環境変数が無効な場合はUTCにフォールバックする(self, monkeypatch: pytest.MonkeyPatch):
        # --- Arrange ---
        monkeypatch.setenv("TZ", "Invalid/Zone")
        ts = 0

        # --- Act ---
        result = format_unix_timestamp(ts)

        # --- Assert ---
        assert result == "1970-01-01 00:00:00 UTC"

    def test_TZ空文字の場合はシステムタイムゾーンを使う(self, monkeypatch: pytest.MonkeyPatch):
        # --- Arrange ---
        monkeypatch.setenv("TZ", "")
        # システムタイムゾーンに依存するため、UTC オフセットが含まれることだけを確認する
        ts = 1_700_000_000

        # --- Act ---
        result = format_unix_timestamp(ts)

        # --- Assert ---
        # "YYYY-MM-DD HH:MM:SS <TZ名>" の形式であることを確認
        parts = result.split(" ")
        assert len(parts) == 3
        assert len(parts[0]) == 10  # YYYY-MM-DD
        assert len(parts[1]) == 8  # HH:MM:SS


class TestResolveTz:
    def test_TZ未設定ならシステムタイムゾーンを返す(self, monkeypatch: pytest.MonkeyPatch):
        # --- Arrange ---
        monkeypatch.delenv("TZ", raising=False)

        # --- Act ---
        result = _resolve_tz()

        # --- Assert ---
        # UTC ではなくシステムタイムゾーン（/etc/localtime）が返る
        assert result is not None
        assert result != timezone.utc or _system_is_utc()

    def test_有効なTZならZoneInfoを返す(self, monkeypatch: pytest.MonkeyPatch):
        # --- Arrange ---
        monkeypatch.setenv("TZ", "America/New_York")

        # --- Act ---
        result = _resolve_tz()

        # --- Assert ---
        assert result == ZoneInfo("America/New_York")

    def test_無効なTZならUTCを返す(self, monkeypatch: pytest.MonkeyPatch):
        # --- Arrange ---
        monkeypatch.setenv("TZ", "Not/AZone")

        # --- Act ---
        result = _resolve_tz()

        # --- Assert ---
        assert result == timezone.utc


def _system_is_utc() -> bool:
    """システムタイムゾーンが UTC かどうかを返す（テスト補助関数）。"""
    from datetime import datetime

    offset = datetime.now(timezone.utc).astimezone().utcoffset()
    return offset is not None and offset.total_seconds() == 0
