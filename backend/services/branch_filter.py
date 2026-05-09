"""リモートトラッキングブランチのフィルタリング。"""

from __future__ import annotations

from backend.models import Branch


def filter_synced_remote_branches(branches: list[Branch]) -> list[Branch]:
    """同期済みリモートブランチを除外する。

    ローカルブランチと同じ先端コミットを持つリモートブランチを除外する。
    乖離している場合（tip が異なる場合）はリモートブランチを残す。

    Args:
        branches: ローカル・リモート混在のブランチリスト。

    Returns:
        同期済みリモートブランチを除いたリスト。
    """
    local_tips = {b.name: b.tip_hash for b in branches if b.is_remote == 0}
    return [b for b in branches if not _is_synced_remote(b, local_tips)]


def _is_synced_remote(branch: Branch, local_tips: dict[str, str]) -> bool:
    """ローカルと同期済みのリモートブランチかどうかを判定する。

    Args:
        branch: 判定対象のブランチ。
        local_tips: ローカルブランチ名 → tip_hash のマップ。

    Returns:
        除外すべき同期済みリモートブランチなら True。
    """
    if branch.is_remote == 0:
        return False
    short_name = branch.name.split("/", 1)[1] if "/" in branch.name else branch.name
    return local_tips.get(short_name) == branch.tip_hash
