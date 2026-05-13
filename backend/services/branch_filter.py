"""リモートトラッキングブランチのフィルタリング。"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.models import Branch


@dataclass
class BranchCategories:
    """ブランチ分類の結果。"""

    local: list[Branch] = field(default_factory=list)
    synced_remotes: list[Branch] = field(default_factory=list)
    diverged_remotes: list[Branch] = field(default_factory=list)


def categorize_branches(branches: list[Branch]) -> BranchCategories:
    """ブランチをローカル・同期済みリモート・乖離リモートに分類する。

    同期済みリモートの判定は tip_hash で行う（名前は問わない）。
    これにより origin/HEAD のような特殊なリモートも正しく分類できる。

    Args:
        branches: ローカル・リモート混在のブランチリスト。

    Returns:
        分類済み BranchCategories。
    """
    local = [b for b in branches if b.is_remote == 0]
    local_tips = {b.tip_hash for b in local}
    cats = BranchCategories(local=local)
    for b in branches:
        if b.is_remote == 0:
            continue
        if b.tip_hash in local_tips:
            cats.synced_remotes.append(b)
        else:
            cats.diverged_remotes.append(b)
    return cats


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
