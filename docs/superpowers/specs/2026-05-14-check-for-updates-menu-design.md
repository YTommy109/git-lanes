# Check for Updates — Mac メニュー機能 設計書

<!-- derived-from ./docs/specification.md -->
<!-- constrained-by ./docs/architecture.md -->

## 概要

Mac のメニューバーに「Check for Updates...」を追加し、ユーザーが任意のタイミングで
アップデートを確認できるようにする。

- **最新状態のとき**: 「v0.6.5 は最新バージョンです」を小さなウィンドウで表示。× で閉じる。
- **更新があるとき**: ダウンロード → 進捗 → インストール・再起動 まで同ウィンドウで完結。

---

## ユーザーストーリー

```
As a Git Lanes ユーザー
I want to メニューバーから手動でアップデートを確認したい
So that 自分のタイミングで最新バージョンへ更新できる
```

---

## 全体フロー

```
Mac メニュー "Check for Updates..."
    ↓ クリック
app.py: _open_update_dialog()
    ├─ update_service.invalidate_cache() でキャッシュをクリア
    ├─ _update_win が既に存在する → focus のみ（2重起動防止）
    └─ webview.create_window("アップデート確認", "/update/dialog", 400×260px)
                                     ↓
                     GET /update/dialog (新エンドポイント)
                                     ↓
                     update_service.check_update()
                                     ↓
                     update_dialog.html (スタンドアロン)
                     ├─ [最新] 「v0.x.x は最新バージョンです」
                     └─ [更新あり] 「v0.x.x が利用可能」
                                 → ダウンロード → 進捗 → インストール
```

---

## コンポーネント設計

### 1. `backend/app.py` — メニュー登録とウィンドウ管理

```python
_update_win: webview.Window | None = None

def _open_update_dialog(port: int) -> None:
    # キャッシュ無効化 → 既存ウィンドウがあればフォーカス → なければ新規作成
    ...

def main() -> None:
    menu = [
        webview.Menu("Git Lanes", [
            webview.MenuAction("Check for Updates...", lambda: _open_update_dialog(port)),
        ])
    ]
    webview.start(menu=menu)
```

**ウィンドウ管理:**

- `_update_win` グローバルで参照を保持
- ウィンドウの `closed` イベントで `_update_win = None` にリセット
- 開く前に `update_service.invalidate_cache()` を呼んでキャッシュをクリア

### 2. `backend/services/update_service.py` — キャッシュ無効化

```python
def invalidate_cache() -> None:
    """更新確認キャッシュを無効化する（次回 check_update で強制再取得）。"""
    _cache["checked_at"] = None
    _cache["result"] = None
```

### 3. `backend/routers/update.py` — ダイアログエンドポイント

```
GET /update/dialog
```

- `check_update()` を呼んで結果を取得
- `update_dialog.html` に `{"available": bool, "version": str, "current_version": str}` を渡す

### 4. `backend/templates/update_dialog.html` — スタンドアロン HTML

base.html を継承しない独立テンプレート。htmx + hyperscript を CDN から読む。

**最新状態のとき:**

```
┌─────────────────────────────────┐
│  ✓ 最新バージョンです            │
│                                 │
│  Git Lanes v0.6.5 は最新です。   │
│                                 │
│            （× で閉じる）         │
└─────────────────────────────────┘
```

**更新があるとき:**

```
┌─────────────────────────────────┐
│  v0.7.0 が利用可能です           │
│                                 │
│  現在: v0.6.5                    │
│  最新: v0.7.0                    │
│                                 │
│  [ダウンロード]                   │
└─────────────────────────────────┘
     ↓ ダウンロード中
┌─────────────────────────────────┐
│  ダウンロード中...               │
│  [========75%=========   ]      │
└─────────────────────────────────┘
     ↓ 完了
┌─────────────────────────────────┐
│  ダウンロード完了                │
│  [インストールして再起動]         │
└─────────────────────────────────┘
```

ダウンロード・インストールボタンは既存の `/api/update/download` / `/api/update/install`
エンドポイントを htmx で呼び出す（既存の `update_progress.html` パーシャルを再利用）。

---

## ウィンドウの閉じ方

OS ネイティブの × ボタンのみ。pywebview JS API の expose は不要。

---

## 既存コードとの関係

| 既存資産 | 扱い |
|---|---|
| `update_service.check_update()` | そのまま再利用 |
| `update_service.download_update()` | そのまま再利用 |
| `update_installer.install_update()` | そのまま再利用 |
| `GET /api/update/check` | サイドバー用として継続維持 |
| `POST /api/update/download` | ダイアログからも呼び出す |
| `POST /api/update/install` | ダイアログからも呼び出す |
| `partials/update_progress.html` | ダイアログ内で `hx-target` 指定して再利用 |
| サイドバーバナー（base.html） | 廃止しない。ウィンドウフォーカス時の自動チェックは継続 |

---

## テスト戦略

### 単体テスト（`tests/unit/`）

| テストケース | 対象 |
|---|---|
| `invalidate_cache` を呼ぶとキャッシュがクリアされる | `update_service.invalidate_cache` |
| `GET /update/dialog` が最新状態のとき 200 を返す | `update.py` |
| `GET /update/dialog` が更新ありのとき 200 を返す | `update.py` |

### E2E テスト（`tests/e2e/`）

| テストケース | 観点 |
|---|---|
| ダイアログで「最新バージョンです」が表示される | ハッピーパス（モック環境） |
| ダイアログで「ダウンロード」ボタンが表示される | 更新ありのハッピーパス |

---

## 対象外（スコープ外）

- サイドバーバナーの廃止・変更
- 自動アップデート（起動時の自動チェックはすでに実装済み）
- Windows / Linux 対応
