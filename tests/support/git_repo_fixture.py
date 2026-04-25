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
