"""EventBus の単体テスト。"""

import asyncio

from backend.services.event_bus import EventBus


def test_notify_後に_subscribe_がイベントを受け取る():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)
        received: list[str] = []

        async def collect():
            async for ev in bus.subscribe("repo1"):
                received.append(ev)
                return

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        bus.notify("repo1")
        await task
        return received

    # --- Act ---
    result = asyncio.run(_run())

    # --- Assert ---
    assert result == ["reload"]


def test_購読者なし時に_notify_がエラーにならない():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)
        bus.notify("no-subscriber")

    # --- Act / Assert ---
    asyncio.run(_run())  # 例外が出なければ OK


def test_複数購読者に全員ブロードキャストされる():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)
        results_a: list[str] = []
        results_b: list[str] = []

        async def collect_a():
            async for ev in bus.subscribe("repo1"):
                results_a.append(ev)
                return

        async def collect_b():
            async for ev in bus.subscribe("repo1"):
                results_b.append(ev)
                return

        task_a = asyncio.create_task(collect_a())
        task_b = asyncio.create_task(collect_b())
        await asyncio.sleep(0)
        bus.notify("repo1")
        await asyncio.gather(task_a, task_b)
        return results_a, results_b

    # --- Act ---
    a, b = asyncio.run(_run())

    # --- Assert ---
    assert a == ["reload"]
    assert b == ["reload"]


def test_異なる_repo_id_には通知されない():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)
        received: list[str] = []

        async def collect():
            async for ev in bus.subscribe("repo-A"):
                received.append(ev)
                return

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        bus.notify("repo-B")  # 別の repo_id に通知
        bus.notify("repo-A")  # 正しい repo_id に通知
        await task
        return received

    # --- Act ---
    result = asyncio.run(_run())

    # --- Assert ---
    assert result == ["reload"]


def test_set_loop_前の_subscribe_は_RuntimeError_を送出する():
    # --- Arrange ---
    bus = EventBus()

    async def _run():
        async for _ in bus.subscribe("repo1"):
            pass

    # --- Act / Assert ---
    import pytest

    with pytest.raises(RuntimeError, match="set_loop"):
        asyncio.run(_run())
