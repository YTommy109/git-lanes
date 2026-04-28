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


def walk_commits_from_branches(repo: pygit2.Repository) -> list[pygit2.Commit]:
    """全ローカルブランチの先端からトポロジカル順にコミットを列挙する。

    HEAD から到達できないブランチのコミットも含む。
    空リポジトリまたはブランチが存在しない場合は空リストを返す。

    Args:
        repo: 対象リポジトリ。

    Returns:
        ``GIT_SORT_TOPOLOGICAL | GIT_SORT_TIME`` で走査した一覧。
    """
    tips = []
    for name in repo.branches.local:
        branch = repo.branches.local.get(name)
        if branch is not None:
            tips.append(branch.peel(pygit2.Commit).id)
    if not tips:
        return []
    sort = SortMode.TOPOLOGICAL | SortMode.TIME
    walker = repo.walk(tips[0], sort)
    for oid in tips[1:]:
        walker.push(oid)
    return list(walker)


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


def iter_tags(repo: pygit2.Repository) -> Iterator[tuple[str, str]]:
    """タグ名とそのコミットハッシュを列挙する。

    軽量タグ・注釈付きタグの両方を対象とする。
    コミット以外を指すタグ（blob 等）はスキップする。

    Args:
        repo: 対象リポジトリ。

    Yields:
        ``(タグ名, コミットのフルハッシュ)``。
    """
    for ref_name in repo.references:
        if not ref_name.startswith("refs/tags/"):
            continue
        tag_name = ref_name[len("refs/tags/") :]
        ref = repo.references[ref_name]
        try:
            commit = ref.peel(pygit2.Commit)
        except pygit2.GitError:
            continue
        yield tag_name, str(commit.id)
