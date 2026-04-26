"""lane_assignment ヘルパーの単体テスト。"""

from backend.models import Branch, Commit
from backend.services.lane_assignment import (
    _assign_lanes,
    _find_connect_hash,
    _find_main_hashes,
)

_REPO_ID = "r1"


def _c(prefix: str, at: int = 0) -> Commit:
    h = prefix * 40
    return Commit(
        hash=h,
        short_hash=h[:7],
        message="m",
        author_name="a",
        author_email="a@b.c",
        committed_at=at,
        repo_id=_REPO_ID,
    )


def _b(name: str, tip_prefix: str) -> Branch:
    return Branch(name=name, repo_id=_REPO_ID, tip_hash=tip_prefix * 40, is_remote=0)


# ── _find_main_hashes ──────────────────────────────────────


def test_find_main_hashes_直線履歴は全コミットを返す():
    # --- Arrange ---
    rows = [_c("c", 3), _c("b", 2), _c("a", 1)]
    parents = {"c" * 40: ["b" * 40], "b" * 40: ["a" * 40]}
    row_set = {r.hash for r in rows}

    # --- Act ---
    result = _find_main_hashes("c" * 40, parents, row_set)

    # --- Assert ---
    assert result == {"c" * 40, "b" * 40, "a" * 40}


def test_find_main_hashes_マージコミットは第1親のみ辿る():
    # --- Arrange ---
    # main: c → b → a
    # feat: d → b (d は main 外)
    rows = [_c("c", 4), _c("d", 3), _c("b", 2), _c("a", 1)]
    parents = {
        "c" * 40: ["b" * 40, "d" * 40],  # c は b(第1親) と d(第2親) を持つマージ
        "d" * 40: ["b" * 40],
        "b" * 40: ["a" * 40],
    }
    row_set = {r.hash for r in rows}

    # --- Act ---
    result = _find_main_hashes("c" * 40, parents, row_set)

    # --- Assert ---
    assert result == {"c" * 40, "b" * 40, "a" * 40}
    assert "d" * 40 not in result


def test_find_main_hashes_visible外は含めない():
    # --- Arrange ---
    rows = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40], "a" * 40: ["z" * 40]}  # z は visible 外
    row_set = {r.hash for r in rows}

    # --- Act ---
    result = _find_main_hashes("b" * 40, parents, row_set)

    # --- Assert ---
    assert result == {"b" * 40, "a" * 40}
    assert "z" * 40 not in result


# ── _find_connect_hash ─────────────────────────────────────


def test_find_connect_hash_ブランチが直接mainのコミットを指す():
    # --- Arrange ---
    main_hashes = {"b" * 40, "a" * 40}
    row_set = {"c" * 40, "b" * 40, "a" * 40}
    parents = {"c" * 40: ["b" * 40]}

    # --- Act ---
    result = _find_connect_hash("c" * 40, parents, main_hashes, row_set, "a" * 40)

    # --- Assert ---
    assert result == "b" * 40


def test_find_connect_hash_tip自体がmain上はtipを返す():
    # --- Arrange ---
    main_hashes = {"b" * 40, "a" * 40}
    row_set = {"b" * 40, "a" * 40}
    parents = {"b" * 40: ["a" * 40]}

    # --- Act ---
    result = _find_connect_hash("b" * 40, parents, main_hashes, row_set, "a" * 40)

    # --- Assert ---
    assert result == "b" * 40


def test_find_connect_hash_visible外はfallbackを返す():
    # --- Arrange ---
    main_hashes = {"a" * 40}
    row_set = {"c" * 40}  # b と a は visible 外
    parents = {"c" * 40: ["b" * 40]}
    fallback = "a" * 40

    # --- Act ---
    result = _find_connect_hash("c" * 40, parents, main_hashes, row_set, fallback)

    # --- Assert ---
    assert result == fallback


# ── _assign_lanes ──────────────────────────────────────


def test_assign_lanes_接続点が上のブランチが内側レーン():
    # --- Arrange ---
    # main: c(row0) → b(row1) → a(row2)
    # feat/x: x → b (row1 で接続)
    # feat/y: y → a (row2 で接続)
    rows = [_c("c", 3), _c("b", 2), _c("a", 1)]
    parents = {
        "c" * 40: ["b" * 40],
        "b" * 40: ["a" * 40],
        "x" * 40: ["b" * 40],
        "y" * 40: ["a" * 40],
    }
    main_branch = _b("main", "c")
    branches = [main_branch, _b("feat/x", "x"), _b("feat/y", "y")]
    main_hashes = {"c" * 40, "b" * 40, "a" * 40}
    row_set = {r.hash for r in rows}
    hash_to_row = {r.hash: i for i, r in enumerate(rows)}

    # --- Act ---
    result = _assign_lanes(branches, main_branch, parents, main_hashes, row_set, hash_to_row, rows)

    # --- Assert ---
    names_by_lane = {bl.lane: bl.name for bl in result}
    assert names_by_lane[1] == "feat/x"  # row1 接続 → 内側
    assert names_by_lane[2] == "feat/y"  # row2 接続 → 外側


def test_assign_lanes_独自コミットなしはhas_unique_commits_false():
    # --- Arrange ---
    rows = [_c("b", 2), _c("a", 1)]
    parents = {"b" * 40: ["a" * 40]}
    main_branch = _b("main", "b")
    branches = [main_branch, _b("hotfix", "b")]  # hotfix は main の先端を指す
    main_hashes = {"b" * 40, "a" * 40}
    row_set = {r.hash for r in rows}
    hash_to_row = {r.hash: i for i, r in enumerate(rows)}

    # --- Act ---
    result = _assign_lanes(branches, main_branch, parents, main_hashes, row_set, hash_to_row, rows)

    # --- Assert ---
    assert len(result) == 1
    assert result[0].has_unique_commits is False
    assert result[0].connect_hash == "b" * 40
