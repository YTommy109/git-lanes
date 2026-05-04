# ブランチ並び順設計書

<!-- derived-from ../../../docs/graph-algorithm.md -->
<!-- constrained-by ../../../docs/architecture.md#svg-グラフの描画方針 -->

## 概要

グラフ上のブランチの左右配置を「フォークポイントが新しいブランチほど左」というルールで決定する。
フォークポイント（分岐元コミット）は SQLite にキャッシュし、グラフ描画時には読み取るだけにする。

## 用語

| 用語 | 定義 |
|---|---|
| フォークポイント | そのブランチが他のブランチの履歴から分岐した直接の親コミット |
| 専有コミット | あるブランチの祖先に含まれ、他のどのブランチの祖先にも含まれないコミット |
| reach[C] | コミット C の子孫にブランチ tip を持つブランチ tip ハッシュの集合 |
| bottom_excl | 各ブランチの専有コミットのうち、トポロジカル順で最も古いもの |

## 並び順ルール

- フォークポイントが**新しい**ブランチほど**左**（小さいレーン番号）に配置する
- フォークポイントが同一のブランチ間は、bottom_excl が新しいブランチを左に置く（tie-break）
- フォークポイントが NULL のブランチ（ルートブランチまたは未計算）は最右に置く

## アーキテクチャ

```
同期処理（sync）
  └─ コミット・ブランチを DB に保存
       ↓
フォークポイント計算（fork_point.py）
  └─ reach 伝播アルゴリズムで計算
  └─ Branch.fork_committed_at / fork_hash を DB に書き込む
       ↓
グラフ描画（grid_builder.py）
  └─ Branch.fork_committed_at でソートして init_branch_maps に渡す
```

## データモデル変更

`Branch` テーブルに以下の 2 カラムを追加する。

| カラム | 型 | 説明 |
|---|---|---|
| `fork_hash` | `TEXT NULL` | フォークポイントのコミットハッシュ |
| `fork_committed_at` | `TIMESTAMP NULL` | フォークポイントのコミット日時（ソートキー） |

`NULL` はルートブランチ（主軸）または未計算を表し、最右に配置する。

tie-break に使う `bottom_excl` の `committed_at` は DB に保存しない。
`fork_point.py` の計算結果をインメモリで保持し、ソート時のみ参照する。

## アルゴリズム

### reach 伝播（新→古のトポロジカル順で 1 パス）

```
children_map を構築: parent_hash → [child_hash, ...]

for commit C in commits（新→古）:
    reach[C] = union(reach[child] for child in children_map[C])
    if C.hash in tip_set:
        reach[C] |= {C.hash}

    if |reach[C]| == 1:
        # C は単一ブランチの専有コミット
        bottom_excl[branch] = C  # 上書きし続けることで最古が残る
```

### フォークポイントの導出

```
for branch B:
    if bottom_excl[B] が存在しない:
        fork_committed_at = NULL  # 最右
    elif bottom_excl[B] が root コミット（親なし）:
        fork_committed_at = NULL  # 最右
    else:
        fork_point = bottom_excl[B].parents[0]
        fork_committed_at = fork_point.committed_at
        fork_hash = fork_point.hash
```

### 具体例

```
コミット（トポロジカル順）: E(0) G(1) D(2) F(3) C(4) B(5) A(6)

main:    A - B - C - D - E   tip=E
feature:         |
                 C - F - G   tip=G

reach:
  E(0): {E}
  G(1): {G}
  D(2): {E}       ← E の子
  F(3): {G}       ← G の子
  C(4): {E, G}    ← D と F の子（複数ブランチ到達）
  B(5): {E, G}
  A(6): {E, G}

専有コミット:
  main    → E(0), D(2)  → bottom_excl = D(2)
  feature → G(1), F(3)  → bottom_excl = F(3)

フォークポイント:
  main    → parent(D) = C → fork_committed_at = C.committed_at
  feature → parent(F) = C → fork_committed_at = C.committed_at

tie-break（bottom_excl の committed_at）:
  main    → D.committed_at（D は F より新しい）→ 左
  feature → F.committed_at → 右
```

## 再計算タイミング

| イベント | 対応 |
|---|---|
| ブランチの tip が変化した | そのブランチのみ再計算 |
| リベース検出（HEAD が祖先でない） | 全ブランチ再計算 |
| 新規ブランチ追加 | そのブランチのみ計算 |

## 変更ファイル一覧

| ファイル | 種別 | 変更内容 |
|---|---|---|
| `docs/graph-algorithm.md` | 修正 | ブランチ並び順ルールを追記 |
| `backend/models.py` | 修正 | Branch に fork_hash・fork_committed_at 追加 |
| `backend/services/fork_point.py` | 新規 | reach アルゴリズム・DB 書き込み |
| `backend/services/grid_builder.py` | 修正 | ソート処理を追加 |
| `tests/unit/test_fork_point.py` | 新規 | fork point 計算の単体テスト（6 ケース） |
| `tests/unit/test_grid_builder.py` | 修正 | ソート挙動のテストを追加（2 ケース） |
| `db/` 以下のマイグレーションファイル | 修正 | カラム追加のマイグレーション |

## テストケース

### test_fork_point.py（新規）

| # | テスト名 | 検証内容 |
|---|---|---|
| 1 | `test_単一ブランチはfork_committed_atがNone` | ブランチが 1 つのみ → NULL |
| 2 | `test_2ブランチの単純分岐でfeatureのforkが正しい` | feature の fork = 分岐点コミット |
| 3 | `test_trunk_ブランチのforkはNone` | main の専有コミットがルートまで届く → NULL |
| 4 | `test_同一forkpoint_はbottom_で順序決定` | 同じ fork → bottom の新旧で左右確定 |
| 5 | `test_複数featureブランチの順序が正しい` | 3 ブランチ → 正しい左右順 |
| 6 | `test_ウィンドウ外コミットはNone扱い` | fork が表示ウィンドウ外 → NULL |

### test_grid_builder.py（追加）

| # | テスト名 | 検証内容 |
|---|---|---|
| 7 | `test_fork_pointが新しいブランチが左レーン` | ソート後のレーン番号確認 |
| 8 | `test_fork_pointがNULLのブランチは右端` | NULL → 最大レーン番号 |

## 計算量

| ステップ | 計算量 |
|---|---|
| children_map 構築 | O(n) |
| reach 伝播 | O(n × m)（n=コミット数, m=ブランチ数） |
| bottom_excl 抽出 | O(n) |
| DB 書き込み | O(m) |

実用規模（n=1000, m=50）では無視できるコスト。
