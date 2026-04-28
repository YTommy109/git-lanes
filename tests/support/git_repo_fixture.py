"""テスト用の Git リポジトリを生成する。"""

from __future__ import annotations

import time
from pathlib import Path

import pygit2


def make_two_commit_repo(path: Path) -> Path:
    """main ブランチにコミットが 2 つあるリポジトリを作成する。

    Args:
        path: リポジトリのルートディレクトリ（存在しなければ作成する）。

    Returns:
        作成したリポジトリのパス。
    """
    path.mkdir(parents=True, exist_ok=True)
    repo = pygit2.init_repository(str(path), False)
    repo.set_head("refs/heads/main")
    sig = pygit2.Signature("テスト", "t@example.com", int(time.time()), 0)
    (path / "a.txt").write_text("a\n", encoding="utf-8")
    repo.index.add("a.txt")
    repo.index.write()
    tree = repo.index.write_tree()
    oid1 = repo.create_commit("refs/heads/main", sig, sig, "first", tree, [])
    (path / "b.txt").write_text("b\n", encoding="utf-8")
    repo.index.add("b.txt")
    repo.index.write()
    tree2 = repo.index.write_tree()
    repo.create_commit("refs/heads/main", sig, sig, "second", tree2, [oid1])
    return path


def make_two_branch_repo(path: Path) -> Path:
    """main と feat ブランチを持つリポジトリを作成する。

    Args:
        path: リポジトリのルートディレクトリ。

    Returns:
        作成したリポジトリのパス。
    """
    path.mkdir(parents=True, exist_ok=True)
    repo = pygit2.init_repository(str(path), False)
    repo.set_head("refs/heads/main")
    sig = pygit2.Signature("テスト", "t@example.com", int(time.time()), 0)

    (path / "a.txt").write_text("a\n", encoding="utf-8")
    repo.index.add("a.txt")
    repo.index.write()
    tree1 = repo.index.write_tree()
    oid1 = repo.create_commit("refs/heads/main", sig, sig, "first", tree1, [])

    commit1 = repo.get(oid1)
    assert isinstance(commit1, pygit2.Commit)
    repo.create_branch("feat", commit1, False)

    (path / "b.txt").write_text("b\n", encoding="utf-8")
    repo.index.add("b.txt")
    repo.index.write()
    tree2 = repo.index.write_tree()
    repo.create_commit("refs/heads/feat", sig, sig, "feat commit", tree2, [oid1])

    (path / "c.txt").write_text("c\n", encoding="utf-8")
    repo.index.add("c.txt")
    repo.index.write()
    tree3 = repo.index.write_tree()
    repo.create_commit("refs/heads/main", sig, sig, "second", tree3, [oid1])

    return path


def make_tagged_repo(path: Path) -> tuple[Path, str, str]:
    """軽量タグと注釈付きタグを持つリポジトリを作成する。

    Args:
        path: リポジトリのルートディレクトリ。

    Returns:
        (リポジトリパス, 軽量タグのコミットハッシュ, 注釈付きタグのコミットハッシュ)
    """
    path.mkdir(parents=True, exist_ok=True)
    repo = pygit2.init_repository(str(path), False)
    repo.set_head("refs/heads/main")
    sig = pygit2.Signature("テスト", "t@example.com", int(time.time()), 0)

    (path / "a.txt").write_text("a\n", encoding="utf-8")
    repo.index.add("a.txt")
    repo.index.write()
    oid1 = repo.create_commit("refs/heads/main", sig, sig, "first", repo.index.write_tree(), [])

    (path / "b.txt").write_text("b\n", encoding="utf-8")
    repo.index.add("b.txt")
    repo.index.write()
    oid2 = repo.create_commit(
        "refs/heads/main", sig, sig, "second", repo.index.write_tree(), [oid1]
    )

    # 軽量タグ: 1 つ目のコミットに付ける
    repo.create_reference("refs/tags/v0.1", oid1, False)

    # 注釈付きタグ: 2 つ目のコミットに付ける
    repo.create_tag("v1.0", oid2, pygit2.enums.ObjectType.COMMIT, sig, "Release 1.0")

    return path, str(oid1), str(oid2)
