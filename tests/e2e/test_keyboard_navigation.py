"""キーボードナビゲーションの E2E テスト。"""

from pathlib import Path

from playwright.sync_api import Page

from tests.support.git_repo_fixture import (
    make_linear_repo,
    make_two_branch_repo,
    make_two_commit_repo,
)

# SVG <g> 要素は Playwright の可視性チェックをパスしないため、
# wait_for_function で直接 DOM を確認する
_WAIT_SELECTED = "document.querySelector('.commit-node.selected') !== null"


def _open_graph(page: Page, base_url: str, repo_path: Path) -> None:
    """リポジトリを登録してグラフ画面を開き、キーボード操作できる状態にする。

    Args:
        page: Playwright のページオブジェクト。
        base_url: テストサーバーのベース URL。
        repo_path: 登録するリポジトリのパス。
    """
    response = page.request.post(f"{base_url}/api/repos", form={"path": str(repo_path)})
    page.goto(response.url)
    page.wait_for_selector(".commit-node")
    # CDN からロードする hyperscript の初期化完了を待機する（SSE があるので networkidle 不可）
    page.wait_for_function("typeof _hyperscript === 'function'")
    # SVG にフォーカスを当ててキーボードナビゲーションを有効化する
    page.locator("#graph-svg").focus()


def _selected_count(page: Page) -> int:
    """選択状態のコミットノード数を返す。

    Args:
        page: Playwright のページオブジェクト。

    Returns:
        .commit-node.selected の要素数。
    """
    return page.evaluate("document.querySelectorAll('.commit-node.selected').length")


def _selected_attr(page: Page, attr: str) -> str:
    """選択中のノードの指定属性値を返す。

    Args:
        page: Playwright のページオブジェクト。
        attr: 取得する属性名（例: "data-lane"）。

    Returns:
        属性値の文字列。
    """
    return page.evaluate(
        f"document.querySelector('.commit-node.selected')?.getAttribute('{attr}') ?? ''"
    )


def test_下キーで最初のノードが選択される(page: Page, base_url: str, tmp_path: Path):
    # Given: グラフ画面が表示されている状態
    repo_path = make_two_commit_repo(tmp_path / "kb-first-select-repo")
    _open_graph(page, base_url, repo_path)

    # When: 下キーを押す
    page.keyboard.press("ArrowDown")

    # Then: いずれかのコミットノードが選択される
    page.wait_for_function(_WAIT_SELECTED)
    assert _selected_count(page) == 1


def test_下キーで同レーンの次コミットに移動する(page: Page, base_url: str, tmp_path: Path):
    # Given: 同レーンに複数コミットが縦に並ぶグラフを開いて最初のノードを選択した状態
    # make_linear_repo はコミットごとにタイムスタンプをずらして異なる row に配置する
    repo_path = make_linear_repo(tmp_path / "kb-down-nav-repo", commit_count=4)
    _open_graph(page, base_url, repo_path)
    page.keyboard.press("ArrowDown")
    page.wait_for_function(_WAIT_SELECTED)

    first_lane = _selected_attr(page, "data-lane")
    first_row = int(_selected_attr(page, "data-row") or "0")

    # When: さらに下キーを押す
    page.keyboard.press("ArrowDown")
    page.wait_for_function(
        f"(() => {{"
        f"  const n = document.querySelector('.commit-node.selected');"
        f"  return n && parseInt(n.getAttribute('data-row')) > {first_row};"
        f"}})()"
    )

    # Then: 同じレーンの次の行のコミットが選択される
    assert _selected_attr(page, "data-lane") == first_lane
    assert int(_selected_attr(page, "data-row") or "0") > first_row


def test_右キーで隣レーンのコミットに移動する(page: Page, base_url: str, tmp_path: Path):
    # Given: グラフ画面を開いてノードを選択した状態（複数レーン必要）
    repo_path = make_two_branch_repo(tmp_path / "kb-right-nav-repo")
    _open_graph(page, base_url, repo_path)
    page.keyboard.press("ArrowDown")
    page.wait_for_function(_WAIT_SELECTED)
    initial_lane = int(_selected_attr(page, "data-lane") or "0")

    # When: 右キーを押す
    page.keyboard.press("ArrowRight")
    # 選択レーンが initial_lane より大きくなるまで待機する
    page.wait_for_function(
        f"(() => {{"
        f"  const n = document.querySelector('.commit-node.selected');"
        f"  return n && parseInt(n.getAttribute('data-lane')) > {initial_lane};"
        f"}})()"
    )

    # Then: より大きいレーン番号のコミットが選択される
    assert int(_selected_attr(page, "data-lane") or "0") > initial_lane


def test_スペースキーでコミット詳細が表示される(page: Page, base_url: str, tmp_path: Path):
    # Given: コミットが選択されている状態
    repo_path = make_two_commit_repo(tmp_path / "kb-space-detail-repo")
    _open_graph(page, base_url, repo_path)
    page.keyboard.press("ArrowDown")
    page.wait_for_function(_WAIT_SELECTED)

    # When: スペースキーを押す
    page.keyboard.press("Space")

    # Then: コミット詳細パネルに内容が表示される
    page.wait_for_function(
        "document.querySelector('#commit-detail') && "
        "document.querySelector('#commit-detail').textContent.trim().length > 0"
    )
    detail = page.evaluate("document.querySelector('#commit-detail')?.textContent ?? ''")
    assert len(detail.strip()) > 0
