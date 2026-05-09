"""リモートブランチのフィルタリング."""

from __future__ import annotations

from backend.models import Branch

def filter_synced_remote_branches(branches: list[Branch]) -> list[Branch]: ...
