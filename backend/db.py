"""エンジン・セッション管理。"""

import logging

from sqlalchemy import create_engine, event, inspect, text
from sqlmodel import Session, SQLModel

from backend.paths import primary_db_path

_logger = logging.getLogger(__name__)

engine = create_engine(
    f"sqlite:///{primary_db_path()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def run_migrations() -> None:
    """モデル定義と実 DB を照合し、不足カラムを ALTER TABLE で追加する。"""
    inspector = inspect(engine)
    for table in SQLModel.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {col["name"] for col in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing:
                continue
            col_type = col.type.compile(engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"))
            _logger.info("マイグレーション: %s.%s を追加", table.name, col.name)


def create_db_and_tables() -> None:
    """テーブルが未存在の場合のみ作成する。"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI の Depends 用セッションジェネレータ。"""
    with Session(engine) as session:
        yield session
