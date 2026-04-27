# アプリ内自動アップデート機能 設計書

作成日: 2026-04-27

---

## 背景と目的

Git Lanes は GitHub Releases（DMG）で配布しているが、Apple Developer ID による公証を行っていない（ad-hoc 署名のみ）。
ブラウザ経由でダウンロードした DMG には `com.apple.quarantine` 拡張属性が付与され、Gatekeeper に毎回引っかかる。
アプリ内で `httpx` を使って直接ダウンロードすれば quarantine が付与されないため、Gatekeeper を回避しながらアップデートを届けられる。

---

## 採用アプローチ

**FastAPI + htmx UI 方式**を採用する。

- バージョンチェック・ダウンロード・インストールを FastAPI のサービス層に実装
- 通知バナーと進捗ダイアログを htmx でレンダリング（既存パターンと一致）
- ダウンロード進捗はポーリング（`hx-trigger="every 1s"`）で取得

---

## 全体フロー

```
[アプリ起動 / ページロード]
  base.html (hx-trigger="load")
    → GET /api/update/check
      → update_service.check_update()
        → GitHub API (1時間TTLキャッシュ)
    ← 更新あり: update_banner.html / 更新なし: 空レスポンス

[ユーザーがダウンロードボタンをクリック]
  → POST /api/update/download
    → バックグラウンドタスクで download_update() 開始
  ← update_progress.html（ポーリング開始）

[1秒ごとのポーリング]
  → GET /api/update/progress
  ← {"percent": 45, "status": "downloading"}
     (status: "idle" | "downloading" | "done" | "error")

[ダウンロード完了後、ユーザーがインストールボタンをクリック]
  → POST /api/update/install
    → hdiutil attach <dmg>  → /Volumes/<アプリ名>/ にマウント
    → /tmp/git-lanes-updater.sh を書き出す（マウントパスを引数として埋め込む）
    → subprocess.Popen(["bash", "/tmp/git-lanes-updater.sh"])
    → sys.exit(0)  ← ブラウザ側は接続断になるが想定内

[updater.sh が実行中]
  sleep 3
  rm -rf "<現在の .app>"
  cp -R "<新 .app>" "<インストール先>"
  hdiutil detach "<マウントポイント>"
  open "<インストール先>/<アプリ名>.app"
```

---

## ファイル構成

### 新規ファイル

| ファイル | 役割 |
|---|---|
| `backend/services/update_service.py` | GitHub API チェック・httpx ダウンロード・インストール処理 |
| `backend/routers/update.py` | 3つの API エンドポイント |
| `backend/templates/partials/update_banner.html` | 更新通知バナー + ダウンロードボタン |
| `backend/templates/partials/update_progress.html` | 進捗バー（ポーリング） |

### 修正ファイル

| ファイル | 変更内容 |
|---|---|
| `backend/templates/base.html` | バナー挿入スロット追加（nav 下部） |
| `backend/main.py` | update ルーターのインクルード |
| `pyproject.toml` | httpx を main 依存へ移動、バージョンを 0.1.4 に更新 |

---

## update_service.py の設計

モジュールレベルで `_cache` と `_download_state` を保持するシンプルなステート管理を採用する。

```python
# モジュールレベルのステート
_cache: dict = {"checked_at": None, "result": None}
_download_state: dict = {"percent": 0, "status": "idle", "dmg_path": None}
```

### 関数一覧

| 関数 | 概要 | 行数目安 |
|---|---|---|
| `check_update() -> dict` | GitHub API で最新バージョンを取得し、現バージョンと比較。1時間TTLキャッシュ | ~25行 |
| `get_download_state() -> dict` | `_download_state` のコピーを返す | ~5行 |
| `download_update(url: str) -> None` | httpx ストリーミングで DMG をダウンロード。進捗を `_download_state` に書き込む | ~25行 |
| `_get_app_path() -> Path \| None` | `sys.frozen` が True のとき、`sys.executable` から `.app` パスを解決 | ~10行 |
| `_write_updater_script(app_path, mount_point, new_app_src) -> Path` | `/tmp/git-lanes-updater.sh` を生成して返す | ~20行 |
| `install_update() -> None` | `hdiutil attach` → コピー → スクリプト起動 → `sys.exit(0)` | ~25行 |

### PyInstaller 環境の判定

```python
# sys.executable = /Applications/Git Lanes.app/Contents/MacOS/Git Lanes
# .app バンドル = exe.parent.parent.parent
def _get_app_path() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).parent.parent.parent
```

---

## API エンドポイント

| メソッド | パス | 説明 | レスポンス |
|---|---|---|---|
| `GET` | `/api/update/check` | 更新確認（1時間TTLキャッシュ） | HTML 断片（バナーまたは空） |
| `POST` | `/api/update/download` | ダウンロード開始（バックグラウンドタスク） | HTML 断片（進捗UI） |
| `GET` | `/api/update/progress` | ダウンロード進捗取得 | JSON `{percent, status}` |
| `POST` | `/api/update/install` | インストールして再起動 | なし（プロセス終了） |

---

## フロントエンド設計

### base.html への追加

```html
<!-- nav 下部に追加 -->
<div id="update-banner"
     hx-get="/api/update/check"
     hx-trigger="load"
     hx-swap="innerHTML">
</div>
```

### update_banner.html

```html
<div class="update-banner">
  <p>新しいバージョン {{ version }} があります</p>
  <button hx-post="/api/update/download"
          hx-target="#update-banner"
          hx-swap="outerHTML">
    ダウンロード
  </button>
</div>
```

### update_progress.html

```html
<!-- status が "done" のときはポーリングを止めるため hx-trigger を除去する -->
<div id="update-progress"
     {% if status != "done" %}
     hx-get="/api/update/progress"
     hx-trigger="every 1s"
     hx-swap="outerHTML"
     {% endif %}>
  <progress value="{{ percent }}" max="100"></progress>
  <span>{{ percent }}%</span>
  {% if status == "done" %}
  <button hx-post="/api/update/install">インストールして再起動</button>
  {% elif status == "error" %}
  <p>ダウンロードに失敗しました</p>
  {% endif %}
</div>
```

---

## テスト戦略

### 単体テスト（`tests/unit/test_update_service.py`）

| テストケース | 概要 |
|---|---|
| `test_check_update_新バージョンあり` | GitHub API をモック → `available=True` を返すことを検証 |
| `test_check_update_最新バージョン` | 同バージョン返却 → `available=False` を検証 |
| `test_check_update_キャッシュが効く` | 2回呼び出しで API 呼び出しが1回のみであることを検証 |
| `test_download_update_進捗更新` | httpx モック + 進捗が 0→100 に変化することを検証 |
| `test_get_app_path_frozen環境` | `sys.frozen=True` をパッチ → `.app` パスが正しく解決されることを検証 |
| `test_get_app_path_開発環境` | `sys.frozen` なし → `None` を返すことを検証 |
| `test_write_updater_script_内容検証` | 生成スクリプトに `hdiutil detach`・`open` が含まれることを検証 |

---

## 制約事項

- PyInstaller バンドル外（開発環境）では `_get_app_path()` が `None` を返すため、インストール処理はスキップしてログを出力する
- ダウンロード中は再度ダウンロードボタンを押せない（`_download_state.status == "downloading"` チェック）
- GitHub API のレートリミット対策として1時間TTLキャッシュを設ける

---

## バージョン変更

- 現在: `0.1.3`
- 変更後: `0.1.4`（この機能追加に対応するパッチバージョンアップ）
