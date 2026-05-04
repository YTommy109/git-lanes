"""WatchService と GitEventHandler の単体テスト。"""

import time
import uuid
from unittest.mock import MagicMock, patch

import pygit2
import pytest
from watchdog.events import FileCreatedEvent, FileModifiedEvent

from backend.services.event_bus import EventBus
from backend.services.watch_service import GitEventHandler, WatchService


@pytest.fixture()
def event_bus():
    """テスト用 EventBus（ループなし）。"""
    return EventBus()


@pytest.fixture()
def mock_engine():
    """テスト用ダミーエンジン。"""
    return MagicMock()


def test_on_modified_後にデバウンスが経過すると_sync_が呼ばれる(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    call_count = 0

    class CountingHandler(GitEventHandler):
        def _sync(self) -> None:
            nonlocal call_count
            call_count += 1

    handler = CountingHandler("repo1", str(tmp_path), event_bus, mock_engine)

    # --- Act ---
    handler.on_modified(FileModifiedEvent(str(tmp_path / ".git" / "HEAD")))
    time.sleep(0.7)  # デバウンス 500ms を超えて待つ

    # --- Assert ---
    assert call_count == 1


def test_連続イベントはデバウンスで1回にまとまる(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    call_count = 0

    class CountingHandler(GitEventHandler):
        def _sync(self) -> None:
            nonlocal call_count
            call_count += 1

    handler = CountingHandler("repo1", str(tmp_path), event_bus, mock_engine)

    # --- Act ---
    handler.on_modified(FileModifiedEvent(str(tmp_path / ".git" / "HEAD")))
    handler.on_modified(FileModifiedEvent(str(tmp_path / ".git" / "refs")))
    handler.on_created(FileCreatedEvent(str(tmp_path / ".git" / "refs" / "heads" / "main")))
    time.sleep(0.7)

    # --- Assert ---
    assert call_count == 1


def test_sync_が_sync_repository_を呼ぶ(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    repo_id = str(uuid.uuid4())
    handler = GitEventHandler(repo_id, str(repo_path), event_bus, mock_engine)

    with patch("backend.services.watch_service.sync_repository") as mock_sync:
        # --- Act ---
        handler._sync()

        # --- Assert ---
        mock_sync.assert_called_once()
        call_args = mock_sync.call_args
        assert call_args.args[1] == repo_id
        assert call_args.args[2] == str(repo_path)


def test_sync_後に_event_bus_notify_が呼ばれる(tmp_path, mock_engine):
    # --- Arrange ---
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    repo_id = str(uuid.uuid4())
    bus = MagicMock(spec=EventBus)
    handler = GitEventHandler(repo_id, str(repo_path), bus, mock_engine)

    with patch("backend.services.watch_service.sync_repository"):
        # --- Act ---
        handler._sync()

        # --- Assert ---
        bus.notify.assert_called_once_with(repo_id)


def test_sync_失敗時に_notify_を呼ばない(tmp_path, mock_engine):
    # --- Arrange ---
    repo_id = str(uuid.uuid4())
    bus = MagicMock(spec=EventBus)
    handler = GitEventHandler(repo_id, str(tmp_path), bus, mock_engine)

    with patch(
        "backend.services.watch_service.sync_repository",
        side_effect=Exception("Git error"),
    ):
        # --- Act ---
        handler._sync()

        # --- Assert ---
        bus.notify.assert_not_called()


def test_watch_service_同一パスの二重登録を防ぐ(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    (tmp_path / ".git").mkdir()
    svc = WatchService(event_bus, mock_engine)

    # --- Act ---
    svc.watch("r1", str(tmp_path))
    svc.watch("r1", str(tmp_path))  # 同じパスを再登録

    # --- Assert ---
    assert len(svc._watched_paths) == 1


def test_watch_service_start_stop_が_observer_を制御する(event_bus, mock_engine):
    # --- Arrange ---
    from unittest.mock import patch

    svc = WatchService(event_bus, mock_engine)

    with (
        patch.object(svc._observer, "start") as mock_start,
        patch.object(svc._observer, "stop") as mock_stop,
        patch.object(svc._observer, "join") as mock_join,
    ):
        # --- Act ---
        svc.start()
        svc.stop()

        # --- Assert ---
        mock_start.assert_called_once()
        mock_stop.assert_called_once()
        mock_join.assert_called_once()


def test_on_created_がデバウンスを呼ぶ(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    from watchdog.events import FileCreatedEvent

    call_count = 0

    class CountingHandler(GitEventHandler):
        def _sync(self) -> None:
            nonlocal call_count
            call_count += 1

    handler = CountingHandler("repo1", str(tmp_path), event_bus, mock_engine)

    # --- Act ---
    handler.on_created(FileCreatedEvent(str(tmp_path / "newfile")))
    time.sleep(0.7)

    # --- Assert ---
    assert call_count == 1


def test_on_deleted_がデバウンスを呼ぶ(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    from watchdog.events import FileDeletedEvent

    call_count = 0

    class CountingHandler(GitEventHandler):
        def _sync(self) -> None:
            nonlocal call_count
            call_count += 1

    handler = CountingHandler("repo1", str(tmp_path), event_bus, mock_engine)

    # --- Act ---
    handler.on_deleted(FileDeletedEvent(str(tmp_path / "gone")))
    time.sleep(0.7)

    # --- Assert ---
    assert call_count == 1


def test_on_moved_がデバウンスを呼ぶ(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    from watchdog.events import FileMovedEvent

    call_count = 0

    class CountingHandler(GitEventHandler):
        def _sync(self) -> None:
            nonlocal call_count
            call_count += 1

    handler = CountingHandler("repo1", str(tmp_path), event_bus, mock_engine)

    # --- Act ---
    handler.on_moved(FileMovedEvent(str(tmp_path / "old"), str(tmp_path / "new")))
    time.sleep(0.7)

    # --- Assert ---
    assert call_count == 1


def test_sync_リポジトリパスが存在しない場合にon_missingが呼ばれる(
    tmp_path, event_bus, mock_engine
):
    # --- Arrange ---
    missing_path = tmp_path / "nonexistent"
    called = []
    handler = GitEventHandler(
        "repo1",
        str(missing_path),
        event_bus,
        mock_engine,
        on_missing=lambda: called.append(True),
    )

    # --- Act ---
    handler._sync()

    # --- Assert ---
    assert called == [True]


def test_sync_リポジトリパスが存在しない場合にnotifyを呼ばない(tmp_path, mock_engine):
    # --- Arrange ---
    missing_path = tmp_path / "nonexistent"
    bus = MagicMock(spec=EventBus)
    handler = GitEventHandler("repo1", str(missing_path), bus, mock_engine)

    # --- Act ---
    handler._sync()

    # --- Assert ---
    bus.notify.assert_not_called()


def test_watch_service_git_ディレクトリが存在しないパスのwatch登録をスキップする(
    tmp_path, event_bus, mock_engine
):
    # --- Arrange ---
    svc = WatchService(event_bus, mock_engine)
    missing_path = tmp_path / "nonexistent"

    # --- Act ---
    svc.watch("r1", str(missing_path))

    # --- Assert ---
    assert len(svc._watched_paths) == 0


def test_watch_service_unwatch_で監視パスが除去される(tmp_path, event_bus, mock_engine):
    # --- Arrange ---
    (tmp_path / ".git").mkdir()
    svc = WatchService(event_bus, mock_engine)
    svc.watch("r1", str(tmp_path))
    git_dir = str(tmp_path / ".git")
    assert git_dir in svc._watched_paths

    # --- Act ---
    svc._unwatch(git_dir)

    # --- Assert ---
    assert git_dir not in svc._watched_paths
