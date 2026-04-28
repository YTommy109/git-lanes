# タグ表示機能 設計書

## 概要

コミットに付けられた Git タグをグラフ画面および詳細パネルに表示する。

## 表示仕様

- **SVGグラフ**: タグが付いたコミット円の横にタグ名をカンマ区切りで表示（例: `v1.0.0, v1.1.0`）
- **詳細パネル**: 選択コミットのタグ一覧を「タグ」フィールドとして表示
- **対象タグ**: 軽量タグ・注釈付きタグの両方
- **複数タグ**: カンマ区切りで全て表示

## データ層

### Tagテーブル（`models.py`）

```python
class Tag(SQLModel, table=True):
    __tablename__ = "tags"
    name: str = Field(primary_key=True)
    repo_id: str = Field(primary_key=True, foreign_key="repositories.id")
    commit_hash: str = Field(foreign_key="commits.hash")
```

- 複合主キー `(name, repo_id)` で一意性を保証
- `Branch` テーブルと同じ構造パターン

### DBスキーマ（`schema.hcl`）

Atlasスキーマに `tags` テーブルを追加し、`uv run task migrate` で反映する。

## Git層（`repositories/git_repo.py`）

```python
def iter_tags(repo: pygit2.Repository) -> Iterator[tuple[str, str]]:
    """タグ名とそのコミットハッシュを列挙する。"""
```

- `refs/tags/` 以下を走査
- 注釈付きタグ（`pygit2.Tag`）は `peel(Commit)` でコミットを取得
- 軽量タグ（`pygit2.Commit`）は直接ハッシュを取得
- それ以外のオブジェクト（blob等）はスキップ

## キャッシュ層（`repositories/cache_repo.py`）

追加する関数：

- `insert_tag_row(session, repo_id, name, commit_hash)` — タグ行を挿入または更新
- `list_tags(session, repo_id)` — リポジトリ全タグを返す
- `get_tags_for_commit(session, repo_id, commit_hash)` — コミットのタグ名リストを返す
- `purge_tags(session, repo_id)` — タグ全削除（`purge_graph_data` から呼ぶ）

## 同期層（`services/sync_service.py`）

`_sync_commits_and_branches` にタグ同期を追加：

```python
for tag_name, commit_hash in iter_tags(repo):
    if cache_repo.get_commit(session, repo_id, commit_hash) is not None:
        cache_repo.insert_tag_row(session, repo_id, tag_name, commit_hash)
```

- ウォーク範囲外のコミットを指すタグはスキップ（外部キー制約違反防止）
- `purge_graph_data` でタグも削除（再同期時のクリーンアップ）

## API層（`routers/html.py`）

### グラフ画面（`/repos/{repo_id}/graph`）

`_build_graph_context` に `tags_by_hash: dict[str, list[str]]` を追加：

```python
tags = cache_repo.list_tags(session, rid)
tags_by_hash = {}
for tag in tags:
    tags_by_hash.setdefault(tag.commit_hash, []).append(tag.name)
```

### 詳細パネル（`/repos/{repo_id}/commits/{commit_hash}/detail`）

`commit_detail` エンドポイントでタグ一覧を取得し、テンプレートに渡す：

```python
tags = cache_repo.get_tags_for_commit(session, rid, ch)
return templates.TemplateResponse(request, "partials/detail.html", {"commit": row, "tags": tags})
```

## テンプレート層

### `graph.html`

タグが付いたコミット円の右にテキスト要素を追加：

```xml
{% if tags_by_hash.get(node.commit.hash) %}
<text x="{{ node.x + 14 }}" y="{{ node.y + 4 }}" font-size="10" fill="#e07b00">
  {{ tags_by_hash[node.commit.hash] | join(", ") }}
</text>
{% endif %}
```

### `partials/detail.html`

タグフィールドを追加：

```html
{% if tags %}
<p><strong>タグ</strong> {{ tags | join(", ") }}</p>
{% endif %}
```

## テスト方針

### 単体テスト

- `iter_tags`: 軽量タグ・注釈付きタグの両方が正しく列挙されること
- `insert_tag_row` / `list_tags` / `get_tags_for_commit`: CRUD動作確認
- `purge_graph_data`: タグも削除されること

### E2Eテスト

- タグが付いたコミットのグラフ表示にタグ名が現れること
- コミット詳細パネルにタグ名が表示されること
