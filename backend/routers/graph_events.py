"""グラフ更新 SSE エンドポイント。"""

from __future__ import annotations

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from backend.services.event_bus import EventBus
from backend.validation import parse_repo_id


def make_router(event_bus: EventBus) -> APIRouter:
    """EventBus を注入したルーターを返す。

    Args:
        event_bus: イベントバスのインスタンス。

    Returns:
        FastAPI ルーター。
    """
    router = APIRouter(tags=["graph-events"])

    @router.get("/repos/{repo_id}/events")
    # EventSourceResponse は FastAPI の OpenAPI スキーマ生成と干渉するため
    # 戻り値型アノテーションを省略する
    async def graph_events(repo_id: str):
        """グラフ更新 SSE ストリームを返す。変化があると event: reload を送信する。"""
        rid = parse_repo_id(repo_id)

        async def _generate():
            async for _ in event_bus.subscribe(rid):
                yield {"event": "reload", "data": ""}

        return EventSourceResponse(_generate())

    return router
