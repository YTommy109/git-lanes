"""watchdog イベントハンドラ。"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session
from watchdog.events import FileSystemEvent, FileSystemEventHandler

from backend.services.event_bus import EventBus
from backend.services.sync_service import sync_repository

_logger = logging.getLogger(__name__)


class GitEventHandler(FileSystemEventHandler):
    """`.git` ディレクトリの変化を検知して同期をトリガーする。"""

    _DEBOUNCE_SEC = 0.5

    def __init__(
        self,
        repo_id: str,
        repo_path: str,
        event_bus: EventBus,
        engine: Engine,
        on_missing: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._repo_id = repo_id
        self._repo_path = repo_path
        self._event_bus = event_bus
        self._engine = engine
        self._timer: threading.Timer | None = None
        self._on_missing = on_missing

    def on_modified(self, event: FileSystemEvent) -> None:
        """ファイル変更イベントを受け取りデバウンスする。"""
        self._debounce()

    def on_created(self, event: FileSystemEvent) -> None:
        """ファイル作成イベントを受け取りデバウンスする。"""
        self._debounce()

    def on_deleted(self, event: FileSystemEvent) -> None:
        """ファイル削除イベントを受け取りデバウンスする。"""
        self._debounce()

    def on_moved(self, event: FileSystemEvent) -> None:
        """ファイル移動イベントを受け取りデバウンスする。"""
        self._debounce()

    def _debounce(self) -> None:
        """連続イベントをまとめて 1 回の同期にする。"""
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self._DEBOUNCE_SEC, self._sync)
        self._timer.start()

    def _sync(self) -> None:
        """同期を実行し、完了後にイベントバスへ通知する。"""
        if not Path(self._repo_path).exists():
            _logger.warning("リポジトリが見つかりません、監視を停止します: %s", self._repo_path)
            if self._on_missing is not None:
                self._on_missing()
            return
        try:
            with Session(self._engine) as session:
                sync_repository(session, self._repo_id, self._repo_path)
        except Exception:
            _logger.exception("リポジトリ同期中にエラーが発生しました: %s", self._repo_id)
            return
        self._event_bus.notify(self._repo_id)
