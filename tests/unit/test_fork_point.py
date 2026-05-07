from __future__ import annotations

from backend.models import Branch, Commit
from backend.services.fork_point import ForkData, compute_fork_data, sort_branches_by_fork_data


def _c(h: str, at: int) -> Commit:
    return Commit(
        hash=h,
        short_hash=h[:7],
        message="",
        author_name="",
        author_email="",
        committed_at=at,
        repo_id="repo1",
    )


def _b(name: str, tip: str) -> Branch:
    return Branch(name=name, repo_id="repo1", tip_hash=tip)


def test_単一ブランチはfork_committed_atがNone():
    # --- Arrange ---
    commits = [_c("B", at=20), _c("A", at=10)]
    parents = {"B": ["A"], "A": []}
    branches = [_b("main", tip="B")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    assert result["main"].fork_committed_at is None
    assert result["main"].fork_hash is None


def test_2ブランチ単純分岐でforkが分岐点コミット():
    # --- Arrange ---
    # E(50) - D(30) - C(20) - B(10) - A(5)  main tip=E
    #                  |
    #                  F(25) - G(40)          feature tip=G
    commits = [
        _c("E", at=50),
        _c("G", at=40),
        _c("D", at=30),
        _c("F", at=25),
        _c("C", at=20),
        _c("B", at=10),
        _c("A", at=5),
    ]
    parents = {
        "E": ["D"],
        "G": ["F"],
        "D": ["C"],
        "F": ["C"],
        "C": ["B"],
        "B": ["A"],
        "A": [],
    }
    branches = [_b("main", tip="E"), _b("feature", tip="G")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    # どちらの分岐元も C（committed_at=20）
    assert result["main"].fork_committed_at == 20
    assert result["main"].fork_hash == "C"
    assert result["feature"].fork_committed_at == 20
    assert result["feature"].fork_hash == "C"
    # bottom_excl: main=D(30), feature=F(25)
    assert result["main"].bottom_committed_at == 30
    assert result["feature"].bottom_committed_at == 25


def test_自分のtipが他のブランチ親の場合はtip親をフォールバック使用():
    # --- Arrange ---
    # main tip=C、feat-2 は C から分岐 → C の reach が {C, E} となり main に専有コミットなし
    # フォールバック: main の tip(C) の親 B をフォークポイントとして使用する
    commits = [
        _c("E", at=45),
        _c("C", at=30),
        _c("D", at=20),
        _c("B", at=10),
        _c("A", at=5),
    ]
    parents = {
        "E": ["C"],
        "C": ["B"],
        "D": ["B"],
        "B": ["A"],
        "A": [],
    }
    branches = [_b("main", tip="C"), _b("feat-1", tip="D"), _b("feat-2", tip="E")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    assert result["main"].fork_committed_at == 10  # フォールバック: parent(tip C) = B(at=10)
    assert result["main"].bottom_committed_at == 30  # tip C の committed_at
    assert result["feat-1"].fork_committed_at == 10  # parent(D) = B(at=10)
    assert result["feat-2"].fork_committed_at == 30  # parent(E) = C(at=30)


def test_線形履歴スタックブランチのソート順が先端位置順になる():
    # --- Arrange ---
    # A → B(main tip) → C(stack1 tip) → D(stack2 tip) という一直線の履歴
    commits = [_c("D", at=40), _c("C", at=30), _c("B", at=20), _c("A", at=10)]
    parents = {"D": ["C"], "C": ["B"], "B": ["A"], "A": []}
    branches = [_b("main", tip="B"), _b("stack1", tip="C"), _b("stack2", tip="D")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    # stack2 は排他コミット D あり → fork = parent(D) = C(at=30)
    assert result["stack2"].fork_committed_at == 30
    # stack1 は排他コミットなし → フォールバック: tip C の親 B(at=20)
    assert result["stack1"].fork_committed_at == 20
    # main は排他コミットなし → フォールバック: tip B の親 A(at=10)
    assert result["main"].fork_committed_at == 10
    # ソート: stack2(30) > stack1(20) > main(10) → 左から stack2, stack1, main
    sorted_branches = sort_branches_by_fork_data(branches, result)
    assert [b.name for b in sorted_branches] == ["stack2", "stack1", "main"]


def test_同一forkpointはbottom_committed_atが設定される():
    # --- Arrange ---
    commits = [_c("C", at=20), _c("D", at=15), _c("B", at=10), _c("A", at=5)]
    parents = {"C": ["B"], "D": ["B"], "B": ["A"], "A": []}
    branches = [_b("feat-A", tip="C"), _b("feat-B", tip="D")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    assert result["feat-A"].fork_committed_at == 10
    assert result["feat-B"].fork_committed_at == 10
    assert result["feat-A"].bottom_committed_at == 20
    assert result["feat-B"].bottom_committed_at == 15


def test_フォークポイントがウィンドウ外の場合はNone():
    # --- Arrange ---
    # F と E の親 X はウィンドウ内に存在しない
    commits = [_c("F", at=30), _c("E", at=20)]
    parents = {"F": ["X"], "E": ["X"]}
    branches = [_b("main", tip="E"), _b("feature", tip="F")]

    # --- Act ---
    result = compute_fork_data(commits, parents, branches)

    # --- Assert ---
    assert result["main"].fork_committed_at is None
    assert result["feature"].fork_committed_at is None


def test_sort_branches_by_fork_data_でnullが右端になる():
    # --- Arrange ---
    branches = [_b("main", tip="A"), _b("feature", tip="B")]
    fork_data = {
        "main": ForkData(fork_hash=None, fork_committed_at=None, bottom_committed_at=None),
        "feature": ForkData(fork_hash="X", fork_committed_at=50, bottom_committed_at=60),
    }

    # --- Act ---
    result = sort_branches_by_fork_data(branches, fork_data)

    # --- Assert ---
    assert result[0].name == "feature"
    assert result[1].name == "main"


def test_sort_branches_by_fork_data_で同一forkはbottomで順序決定():
    # --- Arrange ---
    branches = [_b("feat-A", tip="C"), _b("feat-B", tip="D")]
    fork_data = {
        "feat-A": ForkData(fork_hash="B", fork_committed_at=10, bottom_committed_at=20),
        "feat-B": ForkData(fork_hash="B", fork_committed_at=10, bottom_committed_at=15),
    }

    # --- Act ---
    result = sort_branches_by_fork_data(branches, fork_data)

    # --- Assert ---
    # bottom が新しい feat-A (at=20) が左
    assert result[0].name == "feat-A"
    assert result[1].name == "feat-B"
