"""sync_service の単体テスト。"""

import uuid

import pygit2

from backend.repositories import cache_repo
from backend.services import sync_service
from backend.services.sync_service import _should_resync
from tests.support.git_repo_fixture import make_two_commit_repo


def test_sync_repository_writes_commits(session, tmp_path):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    assert cache_repo.count_commits(session, repo_id) == 2
    rec = cache_repo.get_repository(session, repo_id)
    assert rec is not None
    assert rec.cached_head is not None


def test_sync_repository_handles_empty_repo(session, tmp_path):
    # --- Arrange ---
    repo_path = tmp_path / "empty"
    repo_path.mkdir()
    pygit2.init_repository(str(repo_path), False)
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "empty")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    assert cache_repo.count_commits(session, repo_id) == 0


def test_sync_repository_非HEADブランチのコミットも同期される(session, tmp_path):
    # --- Arrange ---
    # make_two_branch_repo: main(HEAD) に 2 コミット、feat に 1 固有コミット
    from tests.support.git_repo_fixture import make_two_branch_repo

    repo_path = make_two_branch_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    # first(共有) + second(main) + feat_commit(feat) = 3 件
    assert cache_repo.count_commits(session, repo_id) == 3


def test_sync_repository_タグが同期される(session, tmp_path):
    # --- Arrange ---
    from tests.support.git_repo_fixture import make_tagged_repo

    repo_path, hash1, hash2 = make_tagged_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    tags = cache_repo.list_tags(session, repo_id)
    tag_map = {t.name: t.commit_hash for t in tags}
    assert tag_map == {"v0.1": hash1, "v1.0": hash2}


def test_sync_repository_タグなしリポジトリはタグ0件(session, tmp_path):
    # --- Arrange ---
    # タグなしリポジトリで同期後、タグが 0 件であること
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    assert cache_repo.list_tags(session, repo_id) == []


def test_sync_repository_既存コミット先端の新ブランチが同期される(session, tmp_path):
    # --- Arrange ---
    # 初回同期後、同じコミットに新ブランチを追加する（git switch -c 相当）
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")
    sync_service.sync_repository(session, repo_id, str(repo_path))
    branches_before = {b.name for b in cache_repo.list_branches(session, repo_id)}
    assert "hogehoge" not in branches_before

    # 既存コミットに新ブランチを作成する（HEAD は変わらない）
    repo_pygit = pygit2.Repository(str(repo_path))
    tip_commit = repo_pygit.head.peel(pygit2.Commit)
    repo_pygit.create_branch("hogehoge", tip_commit, False)

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    branches_after = {b.name for b in cache_repo.list_branches(session, repo_id)}
    assert "hogehoge" in branches_after


def test_should_resync_HEAD変化なしでFalseを返す(session, tmp_path):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")
    head_hex = "a" * 40
    cache_repo.update_sync_state(session, repo_id, head_hex)
    cache_repo.insert_commit_row(session, repo_id, head_hex, head_hex[:7], "msg", "a", "a@a", 1000)

    # --- Act ---
    result = _should_resync(session, repo_id, head_hex)

    # --- Assert ---
    assert result is False


def test_should_resync_HEAD変化でTrueを返す(session, tmp_path):
    # --- Arrange ---
    repo_path = make_two_commit_repo(tmp_path / "repo")
    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")
    old_head = "a" * 40
    new_head = "b" * 40
    cache_repo.update_sync_state(session, repo_id, old_head)
    cache_repo.insert_commit_row(session, repo_id, old_head, old_head[:7], "msg", "a", "a@a", 1000)

    # --- Act ---
    result = _should_resync(session, repo_id, new_head)

    # --- Assert ---
    assert result is True


def test_sync_repository_ウォーク範囲外のタグはスキップされる(session, tmp_path):
    # --- Arrange ---
    # タグ付きリポジトリを作り、ブランチに属さない孤立コミットにもタグを付ける
    from tests.support.git_repo_fixture import make_tagged_repo

    repo_path, hash1, hash2 = make_tagged_repo(tmp_path / "repo")
    repo_pygit = pygit2.Repository(str(repo_path))
    sig = pygit2.Signature("テスト", "t@example.com", 1000, 0)

    # 孤立コミットを一時ブランチで作成してタグを付け、ブランチを削除する
    (repo_path / "orphan.txt").write_text("x\n", encoding="utf-8")
    repo_pygit.index.read()
    repo_pygit.index.add("orphan.txt")
    repo_pygit.index.write()
    tree = repo_pygit.index.write_tree()
    orphan_oid = repo_pygit.create_commit("refs/heads/tmp-orphan", sig, sig, "orphan", tree, [])
    repo_pygit.create_reference("refs/tags/v-orphan", orphan_oid, False)
    # 孤立コミットをウォーク範囲外にするため一時ブランチを削除する
    repo_pygit.branches.local.get("tmp-orphan").delete()  # type: ignore[union-attr]

    repo_id = str(uuid.uuid4())
    cache_repo.insert_repository(session, repo_id, str(repo_path), "repo")

    # --- Act ---
    sync_service.sync_repository(session, repo_id, str(repo_path))

    # --- Assert ---
    tags = cache_repo.list_tags(session, repo_id)
    tag_names = {t.name for t in tags}
    # v0.1 と v1.0 はウォーク範囲内なので同期される
    assert "v0.1" in tag_names
    assert "v1.0" in tag_names
    # v-orphan はウォーク範囲外（ブランチに属さない）のためスキップされる
    assert "v-orphan" not in tag_names
