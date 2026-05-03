"""アプリケーションログの設定。"""

from __future__ import annotations

import datetime
import logging
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
_LOG_DIR = Path(tempfile.gettempdir()) / "git-lanes"
_timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
_LOG_FILE = _LOG_DIR / f"git-lanes-{_timestamp}.log"


def setup_logging(*, debug: bool = False) -> None:
    """ファイルロガーを設定する。

    Args:
        debug: True のとき DEBUG レベルかつコンソール出力も有効にする。
               False のとき INFO レベルでファイルのみ出力する。
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter(_LOG_FORMAT)

    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=0,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [file_handler]
    if debug:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        handlers.append(stream_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)


def get_log_path() -> Path:
    """現在のログファイルパスを返す。"""
    return _LOG_FILE
