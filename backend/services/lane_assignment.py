"""レーン割り当てのヘルパー関数群。"""

from __future__ import annotations

from backend.models import Branch, Commit
from backend.services.graph_layout import (
    LANE_OFFSET,
    LANE_WIDTH,
    BranchLane,
)
from backend.services.lane_nodes import build_lane_edges, build_lane_nodes

__all__ = [
    "build_lane_edges",
    "build_lane_nodes",
]


def _find_main_hashes(
    tip_hash: str,
    parents: dict[str, list[str]],
    row_set: set[str],
) -> set[str]:
    """main の第1親チェーンに属するハッシュを収集する。

    Args:
        tip_hash: main ブランチの先端ハッシュ。
        parents: 子→親ハッシュのリスト辞書（position 順）。
        row_set: 表示対象コミットのハッシュ集合。

    Returns:
        main チェーン上のハッシュ集合。
    """
    result: set[str] = set()
    current: str | None = tip_hash
    while current and current in row_set:
        result.add(current)
        chain = parents.get(current, [])
        current = chain[0] if chain else None
    return result


def _find_connect_hash(
    tip_hash: str,
    parents: dict[str, list[str]],
    main_hashes: set[str],
    row_set: set[str],
    fallback: str,
) -> str:
    """ブランチ先端から第1親を辿り、main との接続点ハッシュを返す。

    Args:
        tip_hash: ブランチ先端のハッシュ。
        parents: 子→親ハッシュのリスト辞書。
        main_hashes: main チェーンのハッシュ集合。
        row_set: 表示対象コミットのハッシュ集合。
        fallback: visible 外に出た場合に返すハッシュ。

    Returns:
        main 上の接続点ハッシュ。
    """
    current: str | None = tip_hash
    while current and current in row_set:
        if current in main_hashes:
            return current
        chain = parents.get(current, [])
        current = chain[0] if chain else None
    return fallback


def _assign_lanes(
    branches: list[Branch],
    main_branch: Branch,
    parents: dict[str, list[str]],
    main_hashes: set[str],
    row_set: set[str],
    hash_to_row: dict[str, int],
    rows: list[Commit],
) -> list[BranchLane]:
    """main 以外のブランチにレーン番号を割り当てる。

    Args:
        branches: 全ブランチのリスト。
        main_branch: main として扱うブランチ。
        parents: 子→親ハッシュのリスト辞書。
        main_hashes: main チェーンのハッシュ集合。
        row_set: 表示対象コミットのハッシュ集合。
        hash_to_row: ハッシュ→行インデックスの辞書。
        rows: 表示対象コミットのリスト（降順）。

    Returns:
        main 以外の BranchLane のリスト（lane 順）。
    """
    fallback = rows[-1].hash if rows else ""
    items: list[tuple[int, str, str, str, bool, str]] = []
    for br in branches:
        if br.name == main_branch.name:
            continue
        connect = _find_connect_hash(br.tip_hash, parents, main_hashes, row_set, fallback)
        has_unique = br.tip_hash not in main_hashes
        row_idx = hash_to_row.get(connect, len(rows))
        items.append((row_idx, br.tip_hash, br.name, br.tip_hash, has_unique, connect))
    items.sort()
    return [
        BranchLane(
            name=name,
            lane=i + 1,
            tip_hash=tip,
            has_unique_commits=has_unique,
            connect_hash=connect,
            x=(i + 1) * LANE_WIDTH + LANE_OFFSET,
        )
        for i, (_, _, name, tip, has_unique, connect) in enumerate(items)
    ]


def _build_hash_to_lane(
    branch_lanes: list[BranchLane],
    parents: dict[str, list[str]],
    main_hashes: set[str],
    row_set: set[str],
) -> dict[str, int]:
    """各コミットハッシュのレーン番号を返す。

    Args:
        branch_lanes: main 以外の BranchLane リスト。
        parents: 子→親ハッシュのリスト辞書。
        main_hashes: main チェーンのハッシュ集合。
        row_set: 表示対象コミットのハッシュ集合。

    Returns:
        ハッシュ→レーン番号の辞書。
    """
    result: dict[str, int] = {h: 0 for h in main_hashes}
    for bl in branch_lanes:
        if not bl.has_unique_commits:
            continue
        current: str | None = bl.tip_hash
        while current and current in row_set and current not in main_hashes:
            if current not in result:
                result[current] = bl.lane
            chain = parents.get(current, [])
            current = chain[0] if chain else None
    return result
