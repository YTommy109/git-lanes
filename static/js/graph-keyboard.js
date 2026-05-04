/** コミットグラフのキーボードナビゲーション */

const NAV_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']);

function getCommitNodes() {
  return Array.from(document.querySelectorAll('.commit-node'));
}

function coords(node) {
  return {
    lane: parseInt(node.dataset.lane, 10),
    row: parseInt(node.dataset.row, 10),
  };
}

function findSelectedNode() {
  return document.querySelector('.commit-node.selected');
}

/** 同レーン内で delta 方向（+1=下, -1=上）の最近接ノードを返す */
function findVertical(nodes, lane, row, delta) {
  const candidates = nodes.filter((n) => {
    const c = coords(n);
    return c.lane === lane && (delta > 0 ? c.row > row : c.row < row);
  });
  if (!candidates.length) return null;
  return candidates.reduce((best, n) =>
    Math.abs(coords(n).row - row) < Math.abs(coords(best).row - row) ? n : best
  );
}

/** 指定レーンの中で currentRow に最も近いノードを返す */
function findNearestInLane(nodes, targetLane, currentRow) {
  const candidates = nodes.filter((n) => coords(n).lane === targetLane);
  if (!candidates.length) return null;
  return candidates.reduce((best, n) =>
    Math.abs(coords(n).row - currentRow) < Math.abs(coords(best).row - currentRow) ? n : best
  );
}

/** delta 方向の隣レーンに最近接ノードを探す（空レーンをスキップ） */
function findHorizontal(nodes, lane, row, delta) {
  const maxLane = Math.max(...nodes.map((n) => coords(n).lane));
  for (let offset = 1; offset <= maxLane + 1; offset++) {
    const target = lane + delta * offset;
    if (target < 0 || target > maxLane) break;
    const node = findNearestInLane(nodes, target, row);
    if (node) return node;
  }
  return null;
}

/** ↓で次ノードがない場合に intersect センチネルをスクロールさせ次ページロードを試みる */
function tryLoadNextPage(lane, row) {
  const sentinel = document.querySelector('[hx-trigger*="intersect"]');
  if (!sentinel) return;
  sentinel.scrollIntoView({ behavior: 'smooth' });
  document.body.addEventListener(
    'htmx:afterSettle',
    () => {
      const node = findVertical(getCommitNodes(), lane, row, 1);
      if (node) selectNode(node);
    },
    { once: true }
  );
}

/** SVG <g> 要素は click() を持たないため dispatchEvent でクリックを発火する */
function fireClick(node) {
  node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
}

function selectNode(node) {
  fireClick(node);
  node.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function navigate(key) {
  const nodes = getCommitNodes();
  if (!nodes.length) return;

  const selected = findSelectedNode();
  if (!selected) {
    selectNode(nodes[0]);
    return;
  }

  const { lane, row } = coords(selected);
  let target = null;

  if (key === 'ArrowUp') target = findVertical(nodes, lane, row, -1);
  else if (key === 'ArrowDown') {
    target = findVertical(nodes, lane, row, 1);
    if (!target) tryLoadNextPage(lane, row);
  } else if (key === 'ArrowLeft') target = findHorizontal(nodes, lane, row, -1);
  else if (key === 'ArrowRight') target = findHorizontal(nodes, lane, row, 1);

  if (target) selectNode(target);
}

document.addEventListener('keydown', (event) => {
  const svg = document.querySelector('#graph-svg');
  if (!svg) return;
  if (document.activeElement !== svg) return;

  if (event.key === ' ') {
    const selected = findSelectedNode();
    if (selected) {
      event.preventDefault();
      fireClick(selected);
    }
    return;
  }

  if (!NAV_KEYS.has(event.key)) return;
  event.preventDefault();
  navigate(event.key);
});
