"""結合テスト共通フィクスチャ。"""

import pytest

from backend.db import create_db_and_tables


@pytest.fixture(autouse=True)
def _init_db():
    """各統合テスト前にテーブルを作成する。"""
    create_db_and_tables()
    yield
