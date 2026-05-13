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
