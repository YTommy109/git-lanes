from backend.models import Commit
from backend.services.grid_coords import to_svg
from backend.services.grid_models import GridLayout, GridNode

_REPO = "test-repo-id"


def _make_commit(hash: str, at: int = 0) -> Commit:
    return Commit(
        hash=hash,
        short_hash=hash[:7],
        message="テストコミット",
        author_name="Test",
        author_email="test@example.com",
        committed_at=at,
        repo_id=_REPO,
    )


def test_to_svg_assigns_lane_and_row_to_svg_node():
    # --- Arrange ---
    node = GridNode(hash="abc123a", lane=2, row=3, kind="commit", color="#ff0000")
    layout = GridLayout(nodes=[node])
    commits = [_make_commit("abc123a")]

    # --- Act ---
    result = to_svg(layout, commits, {})

    # --- Assert ---
    assert len(result.nodes) == 1
    svg_node = result.nodes[0]
    assert svg_node.lane == 2
    assert svg_node.row == 3


def test_to_svg_assigns_correct_lane_row_for_multiple_nodes():
    # --- Arrange ---
    nodes = [
        GridNode(hash="aaaaaaa", lane=0, row=0, kind="commit", color="#ff0000"),
        GridNode(hash="bbbbbbb", lane=1, row=1, kind="commit", color="#00ff00"),
        GridNode(hash="ccccccc", lane=0, row=2, kind="commit", color="#ff0000"),
    ]
    layout = GridLayout(nodes=nodes)
    commits = [
        _make_commit("aaaaaaa", at=2),
        _make_commit("bbbbbbb", at=1),
        _make_commit("ccccccc", at=0),
    ]

    # --- Act ---
    result = to_svg(layout, commits, {})

    # --- Assert ---
    node_by_hash = {n.commit.hash: n for n in result.nodes}
    assert node_by_hash["aaaaaaa"].lane == 0
    assert node_by_hash["aaaaaaa"].row == 0
    assert node_by_hash["bbbbbbb"].lane == 1
    assert node_by_hash["bbbbbbb"].row == 1
    assert node_by_hash["ccccccc"].lane == 0
    assert node_by_hash["ccccccc"].row == 2
