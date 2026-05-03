# グラフ描画ケース集

<!-- markdownlint-disable MD033 MD036 -->
<!-- constrained-by ./graph-algorithm.md -->

各ケースの「条件」と「期待する表示」を SVG で示す。
確認済みのケースからテストと実装を進める。

用語・座標系・描画ルール・レイアウトアルゴリズムは [graph-algorithm.md](./graph-algorithm.md) を参照する。

---

## ケース 1: コミットが 1 つ（main ブランチのみ）

**条件**

- ブランチが `main` 1 本だけ
- コミットが 1 件のみ

**期待する表示**

- レーン 1 にブランチ名ラベル `main` を −45° 回転して表示する
- その真下にコミットノードを表示する

<svg width="200" height="90" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 2: コミットが 2 つ（直線接続）

**条件**

- ブランチが `main` 1 本だけ
- コミットが 2 件（親子関係が 1 つ）

**期待する表示**

- 新しいコミット（上）と親コミット（下）を縦の直線で結ぶ

<svg width="200" height="130" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="79" x2="50" y2="95" stroke="#4a9cf6" stroke-width="2"/>
  <circle cx="50" cy="102" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 3: 同じコミットを指す 2 つのブランチ

**条件**

- ブランチが `main` と `develop` の 2 本
- 両ブランチが同じコミットを指している（レーン 1 に同居）

**期待する表示**

- ブランチ名ラベルを横に並べて表示する
- コミットノードは 1 つ

<svg width="200" height="90" xmlns="http://www.w3.org/2000/svg">
  <text x="35" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 35, 50)">main</text>
  <text x="65" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 65, 50)">develop</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 4: 2 ブランチが同じ親を持つ

**条件**

- ブランチが `main`（レーン 1）と `develop`（レーン 4）の 2 本
- コミット a の親 = コミット c、コミット b の親 = コミット c（共通の親）

**期待する表示**

- レーン 1: a → c を縦の直線で接続する
- レーン 4: b → c を斜めの直線で接続する（レーン 1 のコミット c へ）

<svg width="210" height="130" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <text x="140" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 140, 50)">develop</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <circle cx="140" cy="72" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="79" x2="50" y2="95" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="140" y1="72" x2="50" y2="102" stroke="#f0883e" stroke-width="2"/>
  <circle cx="50" cy="102" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 5: develop が main の途中から分岐している

**条件**

- main: a2 → a1 → a0（3 コミット）
- develop: b1 → a0（b1 の親は a0）
- b1 は a1 と同じ行（y 位置）に配置する

**期待する表示**

- develop レーンの最上行（a2 と同じ y）にダミーノードを置き、ブランチ名との接続を示す
- ダミーノード → b1 を破線の直線で結ぶ
- b1 → a0 を斜めの直線で結ぶ

<svg width="210" height="155" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <text x="140" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 140, 50)">develop</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <circle cx="140" cy="72" r="3" fill="#f0883e" stroke="#ffffff" stroke-width="1.5"/>
  <line x1="50" y1="79" x2="50" y2="95" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="140" y1="72" x2="140" y2="102" stroke="#f0883e" stroke-width="2" stroke-dasharray="4,3"/>
  <circle cx="50" cy="102" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <circle cx="140" cy="102" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="109" x2="50" y2="125" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="140" y1="102" x2="50" y2="132" stroke="#f0883e" stroke-width="2"/>
  <circle cx="50" cy="132" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 6: develop が古いコミットを指している

**条件**

- main: a2 → a1 → a0（3 コミット）
- develop: a0（develop の tip が a0）

**期待する表示**

- develop レーンの a2 と同じ行にダミーノードを置き、ブランチ名との接続を示す
- ダミーノード → ジョイントノード（a1 と同じ行）を垂直の破線で結ぶ
- ジョイントノード → a0 を斜めの破線で結ぶ
- ジョイントノードは丸印なし

<svg width="210" height="155" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <text x="140" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 140, 50)">develop</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <circle cx="140" cy="72" r="3" fill="#f0883e" stroke="#ffffff" stroke-width="1.5"/>
  <line x1="50" y1="79" x2="50" y2="95" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="140" y1="72" x2="140" y2="102" stroke="#f0883e" stroke-width="2" stroke-dasharray="4,3"/>
  <circle cx="50" cy="102" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="109" x2="50" y2="125" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="140" y1="102" x2="50" y2="132" stroke="#f0883e" stroke-width="2" stroke-dasharray="4,3"/>
  <circle cx="50" cy="132" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 7: develop の方が main より新しい

**条件**

- main: a0（1 コミット）
- develop: b1 → a0（b1 の親は a0）
- b1 は a0 より新しいため、a0 は行 1 に配置される

**期待する表示**

- レーン 1（main）: 最上行にダミーノードを置き、破線で a0 へ接続する
- レーン 4（develop）: b1 を最上行に配置する
- b1 → a0 を斜めの直線で結ぶ

<svg width="210" height="130" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <text x="140" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 140, 50)">develop</text>
  <circle cx="50" cy="72" r="3" fill="#4a9cf6" stroke="#ffffff" stroke-width="1.5"/>
  <circle cx="140" cy="72" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="72" x2="50" y2="102" stroke="#4a9cf6" stroke-width="2" stroke-dasharray="4,3"/>
  <line x1="140" y1="72" x2="50" y2="102" stroke="#f0883e" stroke-width="2"/>
  <circle cx="50" cy="102" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 8: マージ済み・ブランチ名削除済み

**条件**

- main: a1 → [b1, a0]（a1 はマージコミット、第 1 親 = b1、第 2 親 = a0）
- develop: b1 → a0（マージ後にブランチ名を削除済み）
- b1 は a1 より 1 行下に配置される

**期待する表示**

- develop レーンはブランチ名なし → 列幅を通常の 1/3（30px）で描画する
- ダミーノードなし
- a1 から b1 へ斜めの直線（develop 色）
- a1 から a0 へ縦の直線（main 色）
- b1 から a0 へ斜めの直線（develop 色）

<svg width="150" height="155" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="79" x2="50" y2="125" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="50" y1="72" x2="80" y2="102" stroke="#f0883e" stroke-width="2"/>
  <circle cx="80" cy="102" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="80" y1="102" x2="50" y2="132" stroke="#f0883e" stroke-width="2"/>
  <circle cx="50" cy="132" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 9: マージ済み削除ブランチ（コミット複数）

**条件**

- main: a1 → [b3, a0]（マージコミット）
- develop（削除済み、3 コミット）: b3 → b2 → b1 → a0

**期待する表示**

- レーン 2（x=80）: develop 削除済み — b3, b2, b1 を縦に並べる
- a1 → b3 を斜めの直線（develop 色）
- b3 → b2 → b1 を縦の直線（develop 色）
- b1 → a0 を斜めの直線（develop 色）
- a1 → a0 を縦の直線（main 色、レーン 2 をまたいで通過）

<svg width="120" height="210" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="79" x2="50" y2="185" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="50" y1="72" x2="80" y2="102" stroke="#f0883e" stroke-width="2"/>
  <circle cx="80" cy="102" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="80" y1="109" x2="80" y2="125" stroke="#f0883e" stroke-width="2"/>
  <circle cx="80" cy="132" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="80" y1="139" x2="80" y2="155" stroke="#f0883e" stroke-width="2"/>
  <circle cx="80" cy="162" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="80" y1="162" x2="50" y2="192" stroke="#f0883e" stroke-width="2"/>
  <circle cx="50" cy="192" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 10: マージ済み削除ブランチ + 別のアクティブブランチ

**条件**

- main: a1 → [b1, a0]（マージコミット）
- develop（削除済み）: b1 → a0
- feat/something01: c1 → a0

**期待する表示**

- レーン 1（x=50）: main — a1、a0
- レーン 2（x=80）: develop 削除済み — b1、ラベル・ダミーなし
- レーン 4（x=140）: feat/something01 — ダミーノード → c1（破線）、c1 → a0（斜め）

<svg width="180" height="155" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <text x="140" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 140, 50)">feat/something01</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <circle cx="140" cy="72" r="3" fill="#3fb950" stroke="#ffffff" stroke-width="1.5"/>
  <line x1="50" y1="79" x2="50" y2="125" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="50" y1="72" x2="80" y2="102" stroke="#f0883e" stroke-width="2"/>
  <line x1="140" y1="72" x2="140" y2="102" stroke="#3fb950" stroke-width="2" stroke-dasharray="4,3"/>
  <circle cx="80" cy="102" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <circle cx="140" cy="102" r="7" fill="#3fb950" stroke="#ffffff" stroke-width="2"/>
  <line x1="80" y1="102" x2="50" y2="132" stroke="#f0883e" stroke-width="2"/>
  <line x1="140" y1="102" x2="50" y2="132" stroke="#3fb950" stroke-width="2"/>
  <circle cx="50" cy="132" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 11: 2 つのブランチをマージ後にどちらも削除

**条件**

- main: a2 → [c1, a1]（a2 は feat をマージした新しいマージコミット）
- main（前回マージ）: a1 → [b1, a0]（a1 は develop をマージした旧マージコミット）
- develop（削除済み）: b1 → a0
- feat/something01（削除済み）: c1 → a0

**期待する表示**

- レーン 1（x=50）: main — a2、a1、a0
- レーン 2（x=80）: develop 削除済み — b1、ラベル・ダミーなし
- レーン 3（x=110）: feat 削除済み — c1、ラベル・ダミーなし
- a2 → c1 を斜めの直線（feat 色）、a2 → a1 を縦の直線（main 色）
- a1 → b1 を斜めの直線（develop 色）（a1 がマージコミットのため）
- 斜め線は 1 行以内のルールにより c1 → ジョイントノード（row 2）→ a0 と経由する

<svg width="145" height="185" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="79" x2="50" y2="95" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="50" y1="72" x2="110" y2="102" stroke="#3fb950" stroke-width="2"/>
  <circle cx="50" cy="102" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <circle cx="110" cy="102" r="7" fill="#3fb950" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="109" x2="50" y2="155" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="50" y1="102" x2="80" y2="132" stroke="#f0883e" stroke-width="2"/>
  <line x1="110" y1="109" x2="110" y2="132" stroke="#3fb950" stroke-width="2"/>
  <line x1="110" y1="132" x2="50" y2="162" stroke="#3fb950" stroke-width="2"/>
  <circle cx="80" cy="132" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="80" y1="132" x2="50" y2="162" stroke="#f0883e" stroke-width="2"/>
  <circle cx="50" cy="162" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>

---

## ケース 12: 削除済みブランチを 2 段階でマージ

**条件**

- main の tip = a2
- a2 はマージコミット: 第 1 親 = a1（main 継続）、第 2 親 = b1（削除済みブランチ 1）
- b1 は a1 から派生したコミット（b1.親 = a1）
- a1 もマージコミット: 第 1 親 = a0（main 継続）、第 2 親 = b0（削除済みブランチ 2）
- b0 は a0 から派生したコミット（b0.親 = a0）
- 削除済みブランチ 1（b1）・削除済みブランチ 2（b0）はいずれもブランチ名なし

**期待する表示**

- レーン 1（x=50）: main — a2(row=0)、a1(row=2)、a0(row=4)
- レーン 2（x=80）: 削除済みブランチ 1 — b1(row=1)、ラベル・ダミーなし
- レーン 2（x=80）: 削除済みブランチ 2 — b0(row=3)、b1 が a1 に収束した後レーン 2 を再利用、ラベル・ダミーなし
- a2 → a1 を縦の直線で結ぶ（row 差 = 2、main 色）
- a2 → b1 を斜めの直線で結ぶ（削除済みブランチ 1 色）
- b1 → a1 を斜めの直線で結ぶ（削除済みブランチ 1 色）
- a1 → a0 を縦の直線で結ぶ（row 差 = 2、main 色）
- a1 → b0 を斜めの直線で結ぶ（削除済みブランチ 2 色）
- b0 → a0 を斜めの直線で結ぶ（削除済みブランチ 2 色）
- ジョイントノード・ダミーノードは不要

<svg width="140" height="220" xmlns="http://www.w3.org/2000/svg">
  <text x="50" y="50" text-anchor="start" font-size="12" font-family="monospace" fill="#555" transform="rotate(-45, 50, 50)">main</text>
  <circle cx="50" cy="72" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="79" x2="50" y2="125" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="50" y1="72" x2="80" y2="102" stroke="#f0883e" stroke-width="2"/>
  <circle cx="80" cy="102" r="7" fill="#f0883e" stroke="#ffffff" stroke-width="2"/>
  <line x1="80" y1="102" x2="50" y2="132" stroke="#f0883e" stroke-width="2"/>
  <circle cx="50" cy="132" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
  <line x1="50" y1="139" x2="50" y2="185" stroke="#4a9cf6" stroke-width="2"/>
  <line x1="50" y1="132" x2="80" y2="162" stroke="#3fb950" stroke-width="2"/>
  <circle cx="80" cy="162" r="7" fill="#3fb950" stroke="#ffffff" stroke-width="2"/>
  <line x1="80" y1="162" x2="50" y2="192" stroke="#3fb950" stroke-width="2"/>
  <circle cx="50" cy="192" r="7" fill="#4a9cf6" stroke="#ffffff" stroke-width="2"/>
</svg>
