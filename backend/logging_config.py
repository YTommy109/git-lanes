"""アプリケーションログの設定。"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path.home() / "Library" / "Logs" / "git-lanes"
_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def setup_logging() -> None:
    """~/Library/Logs/git-lanes/app.log へのファイルログを設定する。"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        _LOG_DIR / "app.log",
        maxBytes=1024 * 1024,
        backupCount=3,
    )
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logging.basicConfig(level=logging.DEBUG, handlers=[handler])
