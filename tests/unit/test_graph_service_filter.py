"""graph_service のフィルタパラメータのテスト。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.models import Branch
from backend.services.graph_service import sync_and_build


def _local(name: str, tip: str = "aaa") -> Branch:
    return Branch(name=name, repo_id="r1", tip_hash=tip, is_remote=0)


def _remote(name: str, tip: str = "bbb") -> Branch:
    # tip をローカルと意図的に変えて diverged_remote として扱われるようにする
    return Branch(name=name, repo_id="r1", tip_hash=tip, is_remote=1)


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags", return_value=[])
@patch("backend.services.graph_service.branch_repo.list_branches")
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_show_remote_falseのときリモートブランチが除外される(
    mock_sync,
    mock_commits,
    mock_parents,
    mock_list_branches,
    mock_list_tags,
    mock_fork_data,
    mock_persist,
    mock_build,
):
    # --- Arrange ---
    mock_list_branches.return_value = [_local("main"), _remote("origin/main")]
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path", show_remote=False)

    # --- Assert ---
    branches_arg = mock_build.call_args[0][2]
    assert all(b.is_remote == 0 for b in branches_arg)


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags")
@patch("backend.services.graph_service.branch_repo.list_branches", return_value=[])
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_show_tags_falseのときタグが空リストで渡される(
    mock_sync,
    mock_commits,
    mock_parents,
    mock_list_branches,
    mock_list_tags,
    mock_fork_data,
    mock_persist,
    mock_build,
):
    # --- Arrange ---
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path", show_tags=False)

    # --- Assert ---
    tags_arg = mock_build.call_args[0][3]
    assert tags_arg == []
    mock_list_tags.assert_not_called()


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags", return_value=[])
@patch("backend.services.graph_service.branch_repo.list_branches", return_value=[])
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_デフォルトではshow_remoteとshow_tagsがともにtrueになる(
    mock_sync,
    mock_commits,
    mock_parents,
    mock_list_branches,
    mock_list_tags,
    mock_fork_data,
    mock_persist,
    mock_build,
):
    # --- Arrange ---
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path")

    # --- Assert ---
    # tag_repo.list_tags が呼ばれていれば show_tags=True が維持されている
    mock_list_tags.assert_called_once()


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags", return_value=[])
@patch("backend.services.graph_service.branch_repo.list_branches")
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_show_remote_trueのとき同期済みリモートがlabel_only_branchesに渡される(
    mock_sync,
    mock_commits,
    mock_parents,
    mock_list_branches,
    mock_list_tags,
    mock_fork_data,
    mock_persist,
    mock_build,
):
    # --- Arrange ---
    # origin/main は main と同じ tip → synced_remote → label_only に渡るはず
    local_main = Branch(name="main", repo_id="r1", tip_hash="aaa", is_remote=0)
    synced_remote = Branch(name="origin/main", repo_id="r1", tip_hash="aaa", is_remote=1)
    mock_list_branches.return_value = [local_main, synced_remote]
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path", show_remote=True)

    # --- Assert ---
    # branches (位置引数 [2]) にはローカルのみ
    branches_arg = mock_build.call_args[0][2]
    assert all(b.is_remote == 0 for b in branches_arg)
    # label_only_branches (キーワード引数) に synced_remote が入る
    label_only_arg = mock_build.call_args.kwargs["label_only_branches"]
    assert len(label_only_arg) == 1
    assert label_only_arg[0].name == "origin/main"


@patch("backend.services.graph_service.grid_builder.build_grid")
@patch("backend.services.graph_service.persist_fork_points")
@patch("backend.services.graph_service.compute_fork_data", return_value={})
@patch("backend.services.graph_service.tag_repo.list_tags", return_value=[])
@patch("backend.services.graph_service.branch_repo.list_branches")
@patch("backend.services.graph_service.commit_repo.parents_by_child", return_value={})
@patch("backend.services.graph_service.commit_repo.list_all_commits", return_value=[])
@patch("backend.services.graph_service.sync_service.sync_repository")
def test_show_remote_falseのとき同期済みリモートのlabel_only_branchesが空になる(
    mock_sync,
    mock_commits,
    mock_parents,
    mock_list_branches,
    mock_list_tags,
    mock_fork_data,
    mock_persist,
    mock_build,
):
    # --- Arrange ---
    local_main = Branch(name="main", repo_id="r1", tip_hash="aaa", is_remote=0)
    synced_remote = Branch(name="origin/main", repo_id="r1", tip_hash="aaa", is_remote=1)
    mock_list_branches.return_value = [local_main, synced_remote]
    mock_build.return_value = MagicMock()
    session = MagicMock()

    # --- Act ---
    sync_and_build(session, "r1", "/path", show_remote=False)

    # --- Assert ---
    label_only_arg = mock_build.call_args.kwargs["label_only_branches"]
    assert label_only_arg == []
