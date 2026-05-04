"""watchdog Observer によるリポジトリ監視サービス。"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.engine import Engine
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

from backend.services.event_bus import EventBus
from backend.services.watch_event_handler import GitEventHandler

_logger = logging.getLogger(__name__)


def _resolve_git_dir(repo_path: str) -> str:
    """監視する .git ディレクトリのパスを解決する。

    ワークツリーの場合、``gitdir:`` ファイルを解析して共通 ``.git/`` を返す。

    Args:
        repo_path: Git 作業コピーのルートパス。

    Returns:
        監視対象の .git ディレクトリの絶対パス文字列。
    """
    git_path = Path(repo_path) / ".git"
    if git_path.is_dir():
        return str(git_path)
    if git_path.is_file():
        content = git_path.read_text(encoding="utf-8").strip()
        if content.startswith("gitdir:"):
            linked = Path(content[len("gitdir:") :].strip())
            if not linked.is_absolute():
                linked = (git_path.parent / linked).resolve()
            else:
                linked = linked.resolve()
            parts = linked.parts
            if "worktrees" in parts:
                idx = list(parts).index("worktrees")
                return str(Path(*parts[:idx]))
            return str(linked)
    return str(git_path)


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
        git_dir = _resolve_git_dir(repo_path)
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
