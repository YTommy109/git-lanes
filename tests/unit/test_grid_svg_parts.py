"""build_svg_headers() の単体テスト。"""

from backend.services.graph_models import SvgLabel
from backend.services.grid_models import GridBranchLabel, GridLayout, GridNode
from backend.services.grid_svg_parts import build_svg_headers


def test_1ラベルのとき_label_entriesが1件でcy_72():
    # --- Arrange ---
    layout = GridLayout(
        nodes=[],
        branch_labels=[GridBranchLabel(lane=0, names=["main"], color="#4a9cf6")],
    )

    # --- Act ---
    headers = build_svg_headers(layout)

    # --- Assert ---
    assert len(headers) == 1
    assert len(headers[0].label_entries) == 1
    cy, label = headers[0].label_entries[0]
    assert cy == 72.0
    assert label == SvgLabel(text="main", kind="branch")


def test_2ラベルのとき_label_entriesが2件でcy_72_42():
    # --- Arrange ---
    layout = GridLayout(
        nodes=[],
        branch_labels=[GridBranchLabel(lane=0, names=["main", "origin/main"], color="#4a9cf6")],
    )

    # --- Act ---
    headers = build_svg_headers(layout)

    # --- Assert ---
    assert len(headers) == 1
    entries = headers[0].label_entries
    assert len(entries) == 2
    assert entries[0][0] == 72.0  # インデックス 0 が最下段
    assert entries[1][0] == 42.0
    assert entries[0][1] == SvgLabel(text="main", kind="branch")
    assert entries[1][1] == SvgLabel(text="origin/main", kind="branch")


def test_3ラベルのとき_label_entriesが3件でcy_72_42_12():
    # --- Arrange ---
    layout = GridLayout(
        nodes=[],
        branch_labels=[
            GridBranchLabel(lane=0, names=["main", "origin/main", "HEAD"], color="#4a9cf6")
        ],
    )

    # --- Act ---
    headers = build_svg_headers(layout)

    # --- Assert ---
    entries = headers[0].label_entries
    assert len(entries) == 3
    assert entries[0][0] == 72.0
    assert entries[1][0] == 42.0
    assert entries[2][0] == 12.0
    assert entries[0][1] == SvgLabel(text="main", kind="branch")
    assert entries[1][1] == SvgLabel(text="origin/main", kind="branch")
    assert entries[2][1] == SvgLabel(text="HEAD", kind="branch")


def test_ダミーノードがあるとき_connectorが設定される():
    # --- Arrange ---
    layout = GridLayout(
        nodes=[GridNode(hash=None, lane=1, row=0, kind="dummy", color="#f0883e")],
        branch_labels=[GridBranchLabel(lane=1, names=["feature"], color="#f0883e")],
    )

    # --- Act ---
    headers = build_svg_headers(layout)

    # --- Assert ---
    assert headers[0].connector_to_x == 50.0  # GRID_ORIGIN_X(20) + 1*GRID_SPACING(30)
    assert headers[0].connector_to_y == 102.0  # GRID_ORIGIN_Y(102) + 0*GRID_SPACING


def test_ダミーノードがないとき_connectorがNone():
    # --- Arrange ---
    layout = GridLayout(
        nodes=[GridNode(hash="abc1234", lane=0, row=0, kind="commit", color="#4a9cf6")],
        branch_labels=[GridBranchLabel(lane=0, names=["main"], color="#4a9cf6")],
    )

    # --- Act ---
    headers = build_svg_headers(layout)

    # --- Assert ---
    assert headers[0].connector_to_x is None
    assert headers[0].connector_to_y is None
