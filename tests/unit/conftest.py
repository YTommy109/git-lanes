"""単体テスト共通フィクスチャ。"""

import pytest
from sqlalchemy import create_engine, event
from sqlmodel import Session, SQLModel

import backend.models  # noqa: F401 — テーブル登録のため必要


@pytest.fixture(name="session")
def session_fixture():
    """インメモリ SQLite セッションを返す。"""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
