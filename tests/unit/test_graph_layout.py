"""graph_layout の単体テスト。"""

from backend.models import Commit
from backend.services.graph_layout import build_single_lane_layout

_REPO_ID = "test-repo"


def test_build_single_lane_layout_builds_edges_within_visible_set():
    # --- Arrange ---
    rows = [
        Commit(
            hash="b" * 40,
            short_hash="bbbbbbb",
            message="two",
            author_name="a",
            author_email="a@b.c",
            committed_at=2,
            repo_id=_REPO_ID,
        ),
        Commit(
            hash="a" * 40,
            short_hash="aaaaaaa",
            message="one",
            author_name="a",
            author_email="a@b.c",
            committed_at=1,
            repo_id=_REPO_ID,
        ),
    ]
    parents = {rows[0].hash: [rows[1].hash]}

    # --- Act ---
    nodes, edges = build_single_lane_layout(rows, parents)

    # --- Assert ---
    assert len(nodes) == 2
    assert len(edges) == 1
    assert edges[0].child_hash == rows[0].hash
    assert edges[0].parent_hash == rows[1].hash
