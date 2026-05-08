# backend/jinja.py
"""Jinja2 テンプレートエンジンの共有インスタンス。"""

import os
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi.templating import Jinja2Templates


def _resolve_tz() -> tzinfo:
    """タイムゾーンを解決する。TZ 環境変数 → システム設定 → UTC の優先順で返す。

    Returns:
        解決されたタイムゾーンオブジェクト。
    """
    tz_name = os.environ.get("TZ", "").strip()
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, KeyError):
            return timezone.utc
    # TZ 未設定なら /etc/localtime 経由のシステムタイムゾーンを使う
    sys_tz = datetime.now(timezone.utc).astimezone().tzinfo
    return sys_tz if sys_tz is not None else timezone.utc


def format_unix_timestamp(ts: int) -> str:
    """UNIX タイムスタンプを人間が読みやすい日時文字列に変換する。

    Args:
        ts: UNIX タイムスタンプ（秒）。

    Returns:
        "YYYY-MM-DD HH:MM:SS TZ" 形式の日時文字列。
    """
    tz = _resolve_tz()
    dt = datetime.fromtimestamp(ts, tz=tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
templates.env.filters["format_unix_timestamp"] = format_unix_timestamp
