"""結合テスト共通フィクスチャ。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlmodel import Session, SQLModel

from backend.db import get_session
from backend.main import app


@pytest.fixture()
def client(tmp_path):
    """テスト専用 DB を使う TestClient を返す。

    app.dependency_overrides で get_session を差し替えることで、
    本番 DB（~/Library/Application Support/git-lanes/）への書き込みを防ぐ。
    """
    test_engine = create_engine(
        f"sqlite:///{tmp_path}/git-lanes.db",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()
    test_engine.dispose()
