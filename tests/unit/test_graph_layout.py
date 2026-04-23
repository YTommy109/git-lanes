"""graph_layout の単体テスト。"""

from backend.repositories.cache_read import CommitRecord
from backend.services.graph_layout import build_single_lane_layout


def test_build_single_lane_layout_builds_edges_within_visible_set():
    # --- Arrange ---
    rows = [
        CommitRecord(
            hash="b" * 40,
            short_hash="bbbbbbb",
            message="two",
            author_name="a",
            author_email="a@b.c",
            committed_at=2,
        ),
        CommitRecord(
            hash="a" * 40,
            short_hash="aaaaaaa",
            message="one",
            author_name="a",
            author_email="a@b.c",
            committed_at=1,
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
