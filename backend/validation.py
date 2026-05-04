"""HTTP 層向けの入力バリデーション。"""

from __future__ import annotations

import re

from backend.exceptions import CommitNotFoundError, RepositoryNotFoundError

_REPO_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def parse_repo_id(value: str) -> str:
    """リポジトリ ID（UUID）を検証する。"""
    if not _REPO_ID_RE.fullmatch(value):
        raise RepositoryNotFoundError
    return value.lower()


def parse_commit_hash(value: str) -> str:
    """コミットハッシュ（40桁 hex）を検証する。"""
    if not re.fullmatch(r"[0-9a-f]{40}", value, re.IGNORECASE):
        raise CommitNotFoundError
    return value.lower()
