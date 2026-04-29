"""validation の単体テスト。"""

import pytest
from fastapi import HTTPException

from backend.validation import parse_commit_hash, parse_repo_id


def test_parse_repo_id_accepts_lowercase_uuid():
    # --- Arrange ---
    value = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    # --- Act ---
    result = parse_repo_id(value)

    # --- Assert ---
    assert result == value


def test_parse_repo_id_rejects_garbage():
    # --- Arrange ---
    value = "not-a-uuid"

    # --- Act & Assert ---
    with pytest.raises(HTTPException) as exc:
        parse_repo_id(value)
    assert exc.value.status_code == 404


def test_parse_commit_hash_normalizes_case():
    # --- Arrange ---
    h = "a" * 40

    # --- Act ---
    result = parse_commit_hash(h.upper())

    # --- Assert ---
    assert result == h


def test_parse_commit_hash_rejects_invalid():
    # --- Arrange ---
    value = "not-a-hash"

    # --- Act & Assert ---
    with pytest.raises(HTTPException) as exc:
        parse_commit_hash(value)
    assert exc.value.status_code == 404
