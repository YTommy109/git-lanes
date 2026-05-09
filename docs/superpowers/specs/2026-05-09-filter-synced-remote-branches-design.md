# 設計書: 同期済みリモートブランチの非表示化

<!-- derived-from ./docs/specification.md#機能要件 -->

## 概要

ローカルブランチと同じ先端コミット（tip）を持つリモートトラッキングブランチをグラフから除外する。
ブランチが乖離している場合は両方を表示し、差分を可視化する。

**対象仕様**: F-12（リモートブランチの同期状態表示）の基盤実装

---

## 背景と課題

現在、`main` ブランチのみを持つリポジトリでも `main` と `origin/main` が別レーンとして表示される。
ローカルと remote が同じ HEAD を指している場合、2 レーンは冗長であり、ユーザーの期待と乖離している。

---

## 設計方針

<!-- constrained-by ./docs/specification.md#アーキテクチャの重要な決定事項 -->

**DB には全ブランチを保存し続け、表示層でフィルタする。**

- DB のデータを変更しない → 将来の F-12（sync 状態インジケーター）に再利用可能
- sync ロジックを汚さない → 表示の関心事は表示層で完結
- フィルタを外せば元の挙動に戻せる

---

## アーキテクチャ

### 変更前のフロー

```
branch_repo.list_branches()
    ↓（全ブランチ: local + remote）
compute_fork_data()
    ↓
build_grid()  ← origin/main が別レーンに表示される
```

### 変更後のフロー

```
branch_repo.list_branches()
    ↓（全ブランチ: local + remote）
filter_synced_remote_branches()  ← 新規追加
    ↓（同期済みリモートを除外済みリスト）
compute_fork_data()
    ↓
build_grid()  ← origin/main は非表示
```

---

## 新規モジュール

### `backend/services/branch_filter.py`

```
filter_synced_remote_branches(branches: list[Branch]) -> list[Branch]
```

**ロジック:**

1. ローカルブランチから `{short_name: tip_hash}` の辞書を構築する
2. 各リモートブランチについて:
   - `origin/main` → `short_name = "main"`（最初の `/` 以降を抽出）
   - `local_tips.get(short_name) == remote.tip_hash` なら除外
3. ローカルブランチおよび除外されなかったリモートブランチを返す

**ケース別挙動:**

| ローカル | リモート | tip 一致 | 結果 |
|---|---|---|---|
| `main` (abc) | `origin/main` (abc) | ✓ | `main` のみ表示 |
| `main` (abc) | `origin/main` (xyz) | ✗ | 両方表示（乖離） |
| なし | `origin/feature` | — | `origin/feature` 表示 |
| `feature/abc` | `origin/feature/abc` | ✓ | `feature/abc` のみ表示 |

---

## 変更ファイル一覧

| ファイル | 種別 | 変更概要 |
|---|---|---|
| `backend/services/branch_filter.py` | 新規 | `filter_synced_remote_branches()` を定義 |
| `backend/services/graph_service.py` | 修正 | `list_branches()` の直後にフィルタを適用 |
| `tests/unit/services/test_branch_filter.py` | 新規 | フィルタ関数の単体テスト |

---

## テスト戦略

### 単体テスト（AAA スタイル・pytest）

| テストケース | 説明 |
|---|---|
| `test_同名ローカルと同じtipのリモートブランチが除外される` | 基本ケース |
| `test_同名ローカルと異なるtipのリモートブランチは残る` | 乖離ケース |
| `test_対応するローカルブランチがないリモートブランチは残る` | リモートのみ存在 |
| `test_複数リモートが混在する場合でも正しくフィルタされる` | `upstream/main` など |
| `test_ローカルブランチのみの場合は変更なし` | リモートなし |
| `test_空リストは空リストを返す` | 境界値 |

---

## 非対応事項（スコープ外）

- F-11: リモートブランチ表示切り替え（オン/オフ UI）は別タスク
- F-12: 同期状態インジケーター（塗り潰し円 / 波線円）は別タスク
- `origin/HEAD` シンボリック参照の除外: 現状 pygit2 が `peel()` 失敗でスキップしているため影響なし
