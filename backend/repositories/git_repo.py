"""pygit2 を用いた Git リポジトリ読み取り。"""

from __future__ import annotations

from collections.abc import Iterator

import pygit2
from pygit2.enums import SortMode


def open_repository(repo_path: str) -> pygit2.Repository:
    """パスからリポジトリを開く。

    Args:
        repo_path: リポジトリのルートパス。

    Returns:
        開いた ``pygit2.Repository``。

    Raises:
        pygit2.GitError: リポジトリとして開けない場合。
    """
    return pygit2.Repository(repo_path)


def walk_commits_from_head(repo: pygit2.Repository) -> list[pygit2.Commit]:
    """HEAD からトポロジカル順にコミットを列挙する。

    空リポジトリの場合は空リストを返す。

    Args:
        repo: 対象リポジトリ。

    Returns:
        新しいコミットが先頭になるよう ``GIT_SORT_TOPOLOGICAL | GIT_SORT_TIME`` で走査した一覧。
    """
    try:
        tip_oid = repo.head.target
    except (KeyError, pygit2.GitError):
        return []
    sort = SortMode.TOPOLOGICAL | SortMode.TIME
    return list(repo.walk(tip_oid, sort))


def iter_local_branches(repo: pygit2.Repository) -> Iterator[tuple[str, str]]:
    """ローカルブランチ名と先端ハッシュを列挙する。

    Args:
        repo: 対象リポジトリ。

    Yields:
        ``(ブランチ名, 先端コミットのフルハッシュ)``。
    """
    local = repo.branches.local
    for name in local:
        branch = local.get(name)
        if branch is None:
            continue
        tip = branch.peel(pygit2.Commit)
        yield name, str(tip.id)
