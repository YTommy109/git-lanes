# watchdog 自動同期 & SSE リアルタイム更新 — 設計書

作成日: 2026-04-28

---

## 概要

Git リポジトリに変更が生じた際、ユーザーが手動リロードしなくてもグラフ画面に最新コミットが自動表示される機能を追加する。

watchdog が `.git/HEAD` / `.git/refs/` の変化を検知 → SQLite キャッシュを更新 → SSE でブラウザへ通知 → ページリロード、という流れで実現する。

---

## 目的・ユーザー価値

- 現状: 新しいコミットを確認するには画面を手動リロードする必要がある
- 改善後: `git commit` や `git pull` の直後、数秒以内に自動でグラフが更新される

---

## 採用技術

| 技術 | 理由 |
|------|------|
| watchdog（既存依存） | FSEvents ベースでファイル変化を即時検知 |
| SSE（sse-starlette） | プッシュ型通知。ポーリングと違い変化がない間はリクエストが発生しない |
| htmx SSE 拡張 + hyperscript | 既存スタックと統一。JS を新規に書かない |

---

## アーキテクチャ

```
watchdog スレッド
  └─ GitEventHandler.on_modified()
       ├─ sync_service.sync_repository()   # 既存ロジック（独立セッション）
       └─ EventBus.notify(repo_id)         # call_soon_threadsafe で asyncio へ通知

FastAPI (async)
  └─ GET /repos/{repo_id}/events           # SSE ストリーム（sse-starlette）
       └─ EventBus.subscribe(repo_id)      # Queue から "reload" イベントを取り出す

ブラウザ (graph.html)
  └─ hx-ext="sse" sse-connect="/repos/{repo_id}/events"
       └─ on sse:reload → window.location.reload()
```

---

## 新規ファイル・変更ファイル

| ファイル | 種別 | 変更内容 |
|----------|------|----------|
| `backend/services/event_bus.py` | 新規 | repo_id ごとの asyncio.Queue 管理 |
| `backend/services/watch_service.py` | 新規 | watchdog Observer 管理 + GitEventHandler |
| `backend/routers/graph_events.py` | 新規 | `GET /repos/{repo_id}/events` SSE エンドポイント |
| `backend/main.py` | 変更 | lifespan で Observer の起動・停止、登録済みリポジトリの watch を開始 |
| `backend/routers/api.py` | 変更 | リポジトリ登録 API でリポジトリ追加時に `WatchService.watch()` を呼ぶ |
| `backend/templates/graph.html` | 変更 | SSE 接続タグ（hx-ext="sse"）と hyperscript リロードを追加 |
| `pyproject.toml` | 変更 | `sse-starlette>=2.1` 依存追加 |

---

## コンポーネント詳細

### `EventBus`（`backend/services/event_bus.py`）

```python
class EventBus:
    def notify(self, repo_id: str) -> None
        # watchdog スレッドから呼ぶ。call_soon_threadsafe で asyncio ループへ安全に通知。
        # 購読者が存在しない場合は何もしない。

    async def subscribe(self, repo_id: str) -> AsyncGenerator[str, None]
        # SSE エンドポイントが await する非同期ジェネレータ。
        # Queue からイベントを取り出し "reload" を yield する。
        # クライアント切断時は自然にジェネレータが終了する。
```

- repo_id → `list[asyncio.Queue]` のマップをメモリ内で保持
- 同一 repo_id に複数ブラウザタブが接続された場合は全 Queue へブロードキャスト
- シングルトンインスタンスを `backend/services/__init__.py` または `main.py` で管理

### `WatchService`（`backend/services/watch_service.py`）

```python
class WatchService:
    def watch(self, repo_id: str, repo_path: str) -> None
        # Observer にパスを追加。同一パスの二重登録を防ぐ。
        # .git ディレクトリを監視対象とする。

    def start(self) -> None   # Observer.start()
    def stop(self) -> None    # Observer.stop() + join()
```

- 監視対象: `<repo_path>/.git/refs/` と `<repo_path>/.git/HEAD`
- 変化検知 → `sync_service.sync_repository()`（スレッド内・独立 SQLAlchemy セッション）
- 同期完了後 → `event_bus.notify(repo_id)`

### `GitEventHandler`（`watch_service.py` 内）

- `watchdog.events.FileSystemEventHandler` を継承
- `on_modified()` / `on_created()` をフック
- デバウンス: 同一ファイルへの連続イベントを 500ms 以内にまとめる（`threading.Timer` で実装）

### `GET /repos/{repo_id}/events`（`backend/routers/graph_events.py`）

```python
@router.get("/repos/{repo_id}/events")
async def graph_events(repo_id: str) -> EventSourceResponse:
    async def generate():
        async for _ in event_bus.subscribe(repo_id):
            yield ServerSentEvent(data="", event="reload")
    return EventSourceResponse(generate())
```

- `sse-starlette` の `EventSourceResponse` を使用
- クライアント切断時はジェネレータが自然に終了（`asyncio.CancelledError` で補足）
- repo_id はバリデーション済みのものを使用

### `graph.html` の変更

```html
<div
  hx-ext="sse"
  sse-connect="/repos/{{ repo_id }}/events"
  _="on sse:reload call window.location.reload()"
></div>
```

- htmx SSE 拡張の `sse.js` を `<script>` タグで読み込む（CDN または static）
- この要素はグラフコンテナの外（body 直下など）に配置してスコープを明確にする

---

## データフロー（watchdog トリガー時）

```
1. git commit / git pull 等でリポジトリが変化
2. watchdog が .git/refs/ or .git/HEAD の変化を検知（FSEvents）
3. GitEventHandler.on_modified() が発火（デバウンス 500ms）
4. 別スレッド内で sync_service.sync_repository() を実行（独立 SQLAlchemy セッション）
5. 同期完了 → EventBus.notify(repo_id)
6. call_soon_threadsafe で asyncio ループの Queue にイベントを積む
7. SSE ジェネレータが Queue から取り出し → "event: reload\ndata:\n\n" を送信
8. ブラウザの htmx SSE 拡張が受信 → hyperscript: window.location.reload()
9. グラフ画面が再ロード → 最新コミットが表示される
```

---

## スレッド安全性

| 懸念 | 対策 |
|------|------|
| watchdog スレッドから SQLAlchemy を呼ぶ | `with Session(engine) as session` で独立セッションを生成・クローズ |
| watchdog スレッドから asyncio Queue を操作 | `loop.call_soon_threadsafe(queue.put_nowait, event)` を使用 |
| Observer 停止時のレース | `observer.stop()` → `observer.join()` を順に呼ぶ |

---

## エラーハンドリング

- `sync_repository()` が `pygit2.GitError` で失敗した場合: ログに記録し、SSE 通知はスキップ（最後のキャッシュで表示を継続）
- SSE クライアントが切断済みの場合: Queue への書き込みは行うが、ジェネレータ側で `asyncio.CancelledError` を補足して自然に終了

---

## テスト戦略

| テストケース | 種別 | ファイル |
|-------------|------|----------|
| `EventBus.notify()` 後に `subscribe()` がイベントを受け取る | 単体 | `tests/unit/test_event_bus.py` |
| `EventBus` 複数購読者に全員ブロードキャストされる | 単体 | `tests/unit/test_event_bus.py` |
| `EventBus` 購読者なし時に `notify()` がエラーにならない | 単体 | `tests/unit/test_event_bus.py` |
| `WatchService.watch()` で同一パスの二重登録が防がれる | 単体 | `tests/unit/test_watch_service.py` |
| `GitEventHandler.on_modified()` が `.git/HEAD` 変化で `sync_repository()` を呼ぶ | 単体（モック） | `tests/unit/test_watch_service.py` |
| `GitEventHandler` のデバウンスで連続イベントが 1 回にまとまる | 単体 | `tests/unit/test_watch_service.py` |
| `GET /repos/{repo_id}/events` が `event: reload` を返す | 単体（TestClient） | `tests/unit/test_graph_events.py` |

---

## 非対応事項（スコープ外）

- グラフの差分スワップ（ページ全体リロードで十分。スクロール位置保持は将来課題）
- 複数ウィンドウ間のリアルタイム同期（現在はシングルウィンドウ前提）
- ネットワーク越しのリモートリポジトリの変化検知（ローカルのみ）
