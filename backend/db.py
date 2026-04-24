"""エンジン・セッション管理。"""

from sqlalchemy import create_engine, event
from sqlmodel import Session, SQLModel

from backend.paths import primary_db_path

engine = create_engine(
    f"sqlite:///{primary_db_path()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_and_tables() -> None:
    """テーブルが未存在の場合のみ作成する。"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI の Depends 用セッションジェネレータ。"""
    with Session(engine) as session:
        yield session
