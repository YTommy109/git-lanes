"""git_repo ヘルパーの単体テスト。"""

import pygit2

from backend.repositories.git_repo import iter_tags, walk_commits_from_branches
from tests.support.git_repo_fixture import (
    make_tagged_repo,
    make_two_branch_repo,
    make_two_commit_repo,
)


def test_walk_commits_from_branches_全ブランチのコミットを返す(tmp_path):
    # --- Arrange ---
    repo_path = make_two_branch_repo(tmp_path / "repo")
    repo = pygit2.Repository(str(repo_path))

    # --- Act ---
    commits = walk_commits_from_branches(repo)

    # --- Assert ---
    # main に 2 コミット(first, second)、feat に 1 コミット(feat commit)
    # first は共有なので重複せず合計 3 件
    assert len(commits) == 3
    messages = {c.message.strip() for c in commits}
    assert "feat commit" in messages
    assert "second" in messages
    assert "first" in messages


def test_walk_commits_from_branches_空リポジトリは空を返す(tmp_path):
    # --- Arrange ---
    repo_path = tmp_path / "empty"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    pygit2_repo = pygit2.Repository(str(repo_path))

    # --- Act ---
    result = walk_commits_from_branches(pygit2_repo)

    # --- Assert ---
    assert result == []


def test_iter_tags_軽量タグと注釈付きタグを返す(tmp_path):
    # --- Arrange ---
    repo_path, hash1, hash2 = make_tagged_repo(tmp_path / "repo")
    repo = pygit2.Repository(str(repo_path))

    # --- Act ---
    result = dict(iter_tags(repo))

    # --- Assert ---
    assert result == {"v0.1": hash1, "v1.0": hash2}


def test_iter_tags_タグなしは空を返す(tmp_path):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo = pygit2.Repository(str(repo_path))

    # --- Act ---
    result = list(iter_tags(repo))

    # --- Assert ---
    assert result == []
