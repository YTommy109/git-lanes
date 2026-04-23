---
name: implement
description: Git Lanes プロジェクトのコーディング規約に従って実装する。関数・ファイル行数・複雑度・ドックストリング・コメント言語を自動チェックしながら進める。
type: rigid
---

# Git Lanes 実装スキル

このスキルは実装のたびに参照し、すべての制約を満たすことを確認する。

## 実装前の確認

変更対象のファイルを Read して現状の行数を把握する。  
150 行に近いファイルに追記する場合は、先に分割を検討する。

## 実装中のルール

### 関数を書くたびに確認する

```
□ 30 行以内か？
  → 超える場合はヘルパー関数に切り出す

□ 分岐（if / for / while / try）のネストは 3 段以内か？
  → 深い場合はガード節（早期 return）または関数分割で解消する

□ Google スタイルのドックストリングがあるか？（日本語）
  → Args / Returns / Raises を必要な分だけ記載する

□ コメントは日本語か？
  → 英語コメントは書かない
```

### ドックストリングのテンプレート

```python
def function_name(arg: Type) -> ReturnType:
    """一行で何をする関数かを日本語で説明する。

    Args:
        arg: 引数の説明。

    Returns:
        戻り値の説明。

    Raises:
        ExceptionType: 発生条件の説明。
    """
```

戻り値が `None` の場合、Returns セクションは省略する。  
例外を raise しない場合、Raises セクションは省略する。

### ファイルを保存するたびに確認する

```
□ 150 行以内か？（テストコードは対象外）
  → 超える場合はモジュールを分割する

□ D3.js を import していないか？
  → SVG は Jinja2 テンプレートで生成する

□ JavaScript を書いていないか？
  → htmx 属性と hyperscript（_="..."）で表現する

□ subprocess で git コマンドを呼んでいないか？
  → pygit2 の API を使う
```

## アーキテクチャ上の制約

### SVG 生成

```python
# 正しい例: Jinja2 テンプレートで SVG を返す
@router.get("/repos/{repo_id}/graph", response_class=HTMLResponse)
async def get_graph(repo_id: str, request: Request):
    lanes = layout_service.calculate_lanes(repo_id)
    return templates.TemplateResponse("partials/commits.svg.html", {
        "request": request,
        "lanes": lanes,
    })
```

### htmx + hyperscript によるインタラクション

```html
<!-- 正しい例: JS を書かずに hidden を除去する -->
<div
  hidden
  hx-get="/repos/{repo_id}/commits?cursor={hash}&limit=50"
  hx-trigger="intersect threshold:0.1"
  hx-swap="afterend"
  _="on htmx:afterSwap remove @hidden from me"
>
```

### Git 操作

```python
# 正しい例: pygit2 を使う
import pygit2

repo = pygit2.Repository(repo_path)
head = repo.head.peel(pygit2.Commit)

# 誤った例: subprocess は使わない
# result = subprocess.run(["git", "log", ...], ...)
```

### SQLite ファイルパス

```python
from pathlib import Path

def get_db_path(repo_id: str) -> Path:
    """リポジトリ ID から SQLite ファイルパスを返す。"""
    base = Path.home() / "Library" / "Application Support" / "git-lanes"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{repo_id}.db"
```

## 実装後のセルフチェック

実装が終わったら以下を実行して確認する。

```bash
uv run ruff check src/          # Lint
uv run ruff format --check src/ # Format
uv run task test                # テスト
```

問題があれば修正してから PR / コミットに進む。
