"""watchdog Observer によるリポジトリ監視サービス。"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

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


class WatchService:
    """watchdog Observer を管理し、リポジトリの監視を制御する。"""

    def __init__(self, event_bus: EventBus, engine: Engine) -> None:
        self._event_bus = event_bus
        self._engine = engine
        self._observer = Observer()
        self._watched_paths: set[str] = set()
        self._watch_objects: dict[str, ObservedWatch] = {}

    def watch(self, repo_id: str, repo_path: str) -> None:
        """リポジトリの `.git` ディレクトリを監視対象に追加する。

        `.git` ディレクトリが存在しない場合は登録をスキップする。

        Args:
            repo_id: リポジトリ ID。
            repo_path: Git 作業ディレクトリのパス。
        """
        git_dir = str(Path(repo_path) / ".git")
        if git_dir in self._watched_paths:
            return
        if not Path(git_dir).exists():
            _logger.warning("監視スキップ: .git ディレクトリが存在しません: %s", git_dir)
            return
        _logger.info("監視追加: repo_id=%s", repo_id)
        handler = GitEventHandler(
            repo_id,
            repo_path,
            self._event_bus,
            self._engine,
            on_missing=lambda: self._unwatch(git_dir),
        )
        watch_obj: ObservedWatch = self._observer.schedule(handler, git_dir, recursive=True)
        self._watched_paths.add(git_dir)
        self._watch_objects[git_dir] = watch_obj

    def _unwatch(self, git_dir: str) -> None:
        """指定した `.git` ディレクトリの監視を解除する。

        Args:
            git_dir: 監視解除する `.git` ディレクトリのパス。
        """
        if git_dir not in self._watched_paths:
            return
        watch_obj = self._watch_objects.pop(git_dir, None)
        if watch_obj is not None:
            self._observer.unschedule(watch_obj)
        self._watched_paths.discard(git_dir)
        _logger.info("監視解除: %s", git_dir)

    def start(self) -> None:
        """Observer を起動する。lifespan startup で呼ぶ。"""
        self._observer.start()
        _logger.info("WatchService 起動")

    def stop(self) -> None:
        """Observer を停止し、スレッド終了を待つ。lifespan shutdown で呼ぶ。"""
        self._observer.stop()
        self._observer.join()
        _logger.info("WatchService 停止")
