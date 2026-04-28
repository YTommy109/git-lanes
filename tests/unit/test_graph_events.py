"""graph_events ルーターの単体テスト。"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.services.event_bus import EventBus


@pytest.fixture()
def app_with_events():
    """テスト用 FastAPI アプリ（EventBus 付き）。"""
    from backend.routers.graph_events import make_router

    bus = EventBus()
    test_app = FastAPI()
    test_app.include_router(make_router(bus))
    return test_app, bus


def test_events_エンドポイントが_text_event_stream_を返す(app_with_events):
    # --- Arrange ---
    app, _ = app_with_events
    client = TestClient(app, raise_server_exceptions=False)

    # --- Act ---
    with client.stream("GET", "/repos/00000000-0000-0000-0000-000000000001/events") as r:
        # --- Assert ---
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


def test_events_無効な_repo_id_は_404_を返す(app_with_events):
    # --- Arrange ---
    app, _ = app_with_events
    client = TestClient(app, raise_server_exceptions=False)

    # --- Act ---
    r = client.get("/repos/not-a-valid-uuid/events")

    # --- Assert ---
    assert r.status_code == 404
