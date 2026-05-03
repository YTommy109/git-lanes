# グリッド方式コミットグラフ アルゴリズム仕様

日付: 2026-05-01

<!-- supersedes docs/superpowers/specs/2026-04-28-graph-rewrite-design.md -->

## 概要

碁盤の目（グリッド）を座標系とし、各コミットをセルに配置するシンプルな独自アルゴリズム。
gitup の `GIGraph` 実装を参照した従来方式を廃止し、より単純・堅牢な設計に置き換える。

---

## 基本コンセプト

- **列（column）** = ブランチの流れを表す縦のライン
- **行（row）** = コミットの時系列順（上が新しい、下が古い）
- すべてのコミットは `(column, row)` のセルにひとつだけ配置される
- 親子関係のあるコミット間はセル間を結ぶエッジで表現する

---

## Phase 1 — 親コミットの接続

### 入力

- 全コミットのリスト（新しい順にトポロジカルソート済み）

### データ構造

```
active_columns: list[Column]
```

各 `Column` は以下を持つ:

| フィールド | 内容 |
|---|---|
| `index` | 列番号（0 始まり）|
| `bottom` | その列の末尾コミット（まだ親が確定していない最古のコミット）|
| `nodes` | 配置済みコミットのリスト（新→古の順）|

### アルゴリズム

```
1. sorted_commits = トポロジカルソート済みコミット（新→古）

2. active_columns = []

3. sorted_commits の先頭コミットを column[0] に配置し active_columns に追加する。

4. sorted_commits[1:] を順番に処理する:

   for commit C in sorted_commits[1:]:

       placed = False

       for col in active_columns:
           if C is col.bottom の親である:
               col に C を追加（col.bottom を C に更新）
               placed = True
               break

       if not placed:
           新しい列を作り C を配置し active_columns に追加する
```

### フロー詳細（ユーザー記述の言葉で対応）

| ユーザー記述 | アルゴリズムでの対応 |
|---|---|
| 「次のコミットが自分の親であればそのまま」| `C` が `column[0].bottom` の親 → `column[0]` に追加 |
| 「違えば一列右の列にずらす」 | `column[0]` が不一致 → `column[1]`（新規または既存）を確認 |
| 「二列目の親でなければ、一列目の一番下の親か確認」 | `column[1]` も不一致 → `column[0]` の `bottom` と照合 |
| 「どの列にもなければ新しい列として追加しループへ」 | 全列不一致 → `active_columns` に新規列を追加 |

> ポイント: 列の照合は左から右へ順番に行う。最初に一致した列に配置して次のコミットへ進む。

### 親チェックの向き

Git のコミットは「自分の親のハッシュ」を持つ。新→古の順に処理するため、
**列の末尾（新しい側）が、今見ているコミット（古い側）を親として知っているか** を確認する。

```
C.hash in col.bottom.parent_hashes
```

「C が col.bottom の子である」ではなく、「col.bottom が C を自分の親と呼んでいるか」という確認。

---

### 具体例 — 単純な二分岐（マージなし）

以下の履歴を例にする。`root` が共通の始祖で、そこから `main` と `feature` に分岐している。

```
main    : root ← B ← D   (D が最新)
feature : root ← C ← E   (E が最新、root で main から分岐)
```

**親関係まとめ**

| コミット | 親 |
|---|---|
| D | B |
| E | C |
| B | root |
| C | root |
| root | なし |

**トポロジカルソート（新→古）**: D, E, B, C, root

```
step 1: D を col[0] に配置
        active_columns = [ col[0]:[D] ]

step 2: E → col[0].bottom(D).parents = [B]、E ≠ B → 不一致
        新しい col[1] を作り E を配置
        active_columns = [ col[0]:[D]、col[1]:[E] ]

step 3: B → col[0].bottom(D).parents = [B]、B = B → 一致！
        B を col[0] に追加
        active_columns = [ col[0]:[D, B]、col[1]:[E] ]

step 4: C → col[0].bottom(B).parents = [root]、C ≠ root → 不一致
        col[1].bottom(E).parents = [C]、C = C → 一致！
        C を col[1] に追加
        active_columns = [ col[0]:[D, B]、col[1]:[E, C] ]

step 5: root → col[0].bottom(B).parents = [root]、root = root → 一致！
        root を col[0] に追加
        active_columns = [ col[0]:[D, B, root]、col[1]:[E, C] ]
```

**配置結果**

```
row 0:  D         E
row 1:  B         C
row 2:  root
```

```
col:    0         1
```

**エッジ**

| 接続 | 方向 |
|---|---|
| D → B | col[0] 内（縦）|
| B → root | col[0] 内（縦）|
| E → C | col[1] 内（縦）|
| C → root | col[1] から col[0] へ（斜め）|

> `C` と `root` は異なる列にあるため、C → root のエッジは列をまたぐ。
> これが「フィーチャーブランチが main（の祖先）に収束する」様子を表す。

### Phase 1 完了条件

すべてのコミットが何らかの列に配置され、各コミットの親が別のセルに存在する状態。
（`active_columns` のどの `bottom` にも未接続の親が残っていないこと）

---

## Phase 2 以降（未定）

親を繋ぎ終わった後の処理（ブランチ名ラベルの表示・色分け・マージラインの曲線化など）は今後検討する。

---

## 旧設計との比較

| 観点 | 旧設計（gitup GIGraph 方式）| 本設計（グリッド方式）|
|---|---|---|
| 基本構造 | Layer / GraphLine の階層型 | フラットな列リスト |
| ダミーノード | 必要（準備完了判定が複雑）| 不要 |
| 親子接続 | Phase 2〜3 で段階的に解決 | Phase 1 の単一パスで完了 |
| コードの複雑度 | 高（_place_parent / _realize_dummy）| 低（列スキャンのみ）|

---

## 実装上の制約

- 認知的複雑度 10 以下（Ruff C901）
- 関数行数 30 行以内
- ファイル行数 150 行以内（テスト除く）
