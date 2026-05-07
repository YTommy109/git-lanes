"""ブランチのフォークポイント計算・ソート・永続化サービス。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlmodel import Session

from backend.models import Branch, Commit


@dataclass
class ForkData:
    """ブランチのフォークポイント情報。"""

    fork_hash: str | None
    fork_committed_at: int | None
    bottom_committed_at: int | None


def compute_fork_data(
    commits: list[Commit],
    parents: dict[str, list[str]],
    branches: list[Branch],
) -> dict[str, ForkData]:
    """各ブランチのフォークポイントを計算する。

    Args:
        commits: トポロジカル順（新→古）のコミットリスト。
        parents: コミットハッシュ → 親ハッシュリストのマップ。
        branches: ブランチリスト。

    Returns:
        ブランチ名 → ForkData のマップ。
    """
    children_map = _build_children_map(parents)
    commit_by_hash = {c.hash: c for c in commits}
    tip_set = {b.tip_hash for b in branches}
    tip_to_name = {b.tip_hash: b.name for b in branches}
    reach = _compute_reach(commits, children_map, tip_set)
    bottom_excl = _find_bottom_excl(commits, reach, tip_to_name)
    return {b.name: _derive_fork_data(b, bottom_excl, commit_by_hash, parents) for b in branches}


def _build_children_map(parents: dict[str, list[str]]) -> dict[str, list[str]]:
    """親 → 子のマップを構築する。"""
    children: dict[str, list[str]] = defaultdict(list)
    for child, parent_list in parents.items():
        for p in parent_list:
            children[p].append(child)
    return dict(children)


def _compute_reach(
    commits: list[Commit],
    children_map: dict[str, list[str]],
    tip_set: set[str],
) -> dict[str, frozenset[str]]:
    """各コミットに到達可能なブランチ tip ハッシュの集合を計算する。"""
    reach: dict[str, frozenset[str]] = {}
    for commit in commits:
        r: set[str] = set()
        for child in children_map.get(commit.hash, []):
            r |= reach.get(child, frozenset())
        if commit.hash in tip_set:
            r.add(commit.hash)
        reach[commit.hash] = frozenset(r)
    return reach


def _find_bottom_excl(
    commits: list[Commit],
    reach: dict[str, frozenset[str]],
    tip_to_name: dict[str, str],
) -> dict[str, str]:
    """各ブランチの最古の専有コミットハッシュを返す。"""
    bottom: dict[str, str] = {}
    for commit in commits:
        r = reach.get(commit.hash, frozenset())
        if len(r) == 1:
            tip = next(iter(r))
            if tip in tip_to_name:
                bottom[tip_to_name[tip]] = commit.hash
    return bottom


def _derive_fork_data(
    branch: Branch,
    bottom_excl: dict[str, str],
    commit_by_hash: dict[str, Commit],
    parents: dict[str, list[str]],
) -> ForkData:
    """bottom_excl からフォークポイントデータを導出する。

    排他コミットがない場合（線形履歴・後続ブランチによる上書きなど）は
    ブランチ先端コミットの親をフォークポイントとして代用する。
    """
    bottom_hash = bottom_excl.get(branch.name) or branch.tip_hash
    bottom_commit = commit_by_hash.get(bottom_hash)
    if bottom_commit is None:
        return ForkData(fork_hash=None, fork_committed_at=None, bottom_committed_at=None)
    bottom_at = bottom_commit.committed_at
    parent_list = parents.get(bottom_hash, [])
    if not parent_list:
        return ForkData(fork_hash=None, fork_committed_at=None, bottom_committed_at=bottom_at)
    fork_hash = parent_list[0]
    fork_commit = commit_by_hash.get(fork_hash)
    if fork_commit is None:
        return ForkData(fork_hash=fork_hash, fork_committed_at=None, bottom_committed_at=bottom_at)
    return ForkData(
        fork_hash=fork_commit.hash,
        fork_committed_at=fork_commit.committed_at,
        bottom_committed_at=bottom_at,
    )


def sort_branches_by_fork_data(
    branches: list[Branch],
    fork_data: dict[str, ForkData],
) -> list[Branch]:
    """フォークポイントの新しい順にブランチを並べる。None は最右。"""

    def _key(b: Branch) -> tuple[int, int]:
        data = fork_data.get(b.name)
        if data is None or data.fork_committed_at is None:
            return (1, 0)
        return (-data.fork_committed_at, -(data.bottom_committed_at or 0))

    return sorted(branches, key=_key)


def persist_fork_points(
    session: Session,
    branches: list[Branch],
    fork_data: dict[str, ForkData],
) -> None:
    """フォークポイントを Branch レコードに書き込む。変更なしはスキップする。"""
    for branch in branches:
        data = fork_data.get(branch.name)
        if data is None:
            continue
        if (branch.fork_hash, branch.fork_committed_at) == (
            data.fork_hash,
            data.fork_committed_at,
        ):
            continue
        branch.fork_hash = data.fork_hash
        branch.fork_committed_at = data.fork_committed_at
        session.add(branch)
    session.commit()
