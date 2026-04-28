"""リポジトリ更新イベントのバス。watchdog スレッドと asyncio の橋渡し。"""

from __future__ import annotations

import asyncio
import threading
from collections import defaultdict
from typing import AsyncGenerator


class EventBus:
    """repo_id ごとの購読者に更新イベントをブロードキャストする。"""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[str]]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """asyncio ループを登録する。lifespan 起動時に呼ぶこと。

        Args:
            loop: FastAPI が動作する asyncio ループ。
        """
        self._loop = loop

    def notify(self, repo_id: str) -> None:
        """watchdog スレッドから呼ぶ。購読者全員に "reload" を通知する。

        Args:
            repo_id: 更新があったリポジトリ ID。
        """
        if self._loop is None:
            return
        with self._lock:
            queues = list(self._queues.get(repo_id, []))
        for q in queues:
            self._loop.call_soon_threadsafe(q.put_nowait, "reload")

    async def subscribe(self, repo_id: str) -> AsyncGenerator[str, None]:
        """SSE エンドポイントが await する非同期ジェネレータ。

        Args:
            repo_id: 購読するリポジトリ ID。

        Yields:
            イベント文字列（現在は "reload" のみ）。

        Raises:
            RuntimeError: set_loop() が呼ばれる前に subscribe() を呼んだ場合。
        """
        if self._loop is None:
            raise RuntimeError("set_loop() を呼んでから subscribe() を使うこと")
        q: asyncio.Queue[str] = asyncio.Queue()
        with self._lock:
            self._queues[repo_id].append(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            with self._lock:
                self._queues[repo_id].remove(q)


event_bus = EventBus()
