"""コミットのトポロジカルソート。"""

from __future__ import annotations

import heapq

from backend.models import Commit


def topological_sort(rows: list[Commit], parents: dict[str, list[str]]) -> list[Commit]:
    """コミットをトポロジカル順（子が先・親が後）に並べ替える。

    Kahn's algorithm を優先度キュー（committed_at 降順）と組み合わせ、
    クロックスキュー等でタイムスタンプ順がトポロジカル順と一致しない
    場合でも子が常に親より先に表示されることを保証する。

    Args:
        rows: 任意の順序のコミット一覧。
        parents: 子ハッシュをキーとする親ハッシュのリスト。

    Returns:
        トポロジカル順に並んだコミット一覧。
    """
    by_hash = {r.hash: r for r in rows}
    visible = set(by_hash)
    child_count: dict[str, int] = {h: 0 for h in visible}
    for h in visible:
        for ph in parents.get(h, []):
            if ph in visible:
                child_count[ph] = child_count[ph] + 1
    heap: list[tuple[int, str]] = []
    for h, count in child_count.items():
        if count == 0:
            heapq.heappush(heap, (-by_hash[h].committed_at, h))
    result: list[Commit] = []
    while heap:
        _, h = heapq.heappop(heap)
        result.append(by_hash[h])
        for ph in parents.get(h, []):
            if ph not in visible:
                continue
            child_count[ph] -= 1
            if child_count[ph] == 0:
                heapq.heappush(heap, (-by_hash[ph].committed_at, ph))
    return result
