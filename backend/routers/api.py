"""登録などの HTTP API。"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import closing
from pathlib import Path
from typing import Annotated

import pygit2
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse

from backend.paths import primary_db_path
from backend.repositories import cache_read, cache_write
from backend.repositories.git_repo import open_repository

router = APIRouter(tags=["api"])


@router.post("/api/repos")
async def register_repository(path: Annotated[str, Form()]) -> RedirectResponse:
    """フォルダパスからリポジトリを登録し、グラフ画面へリダイレクトする。"""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="ディレクトリが存在しません")
    try:
        open_repository(str(resolved))
    except pygit2.GitError as exc:
        raise HTTPException(status_code=400, detail="Git リポジトリとして開けません") from exc
    repo_id = str(uuid.uuid4())
    with closing(cache_read.connect(str(primary_db_path()))) as conn:
        try:
            cache_write.insert_repository(conn, repo_id, str(resolved), resolved.name)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="このパスは既に登録されています") from exc
    return RedirectResponse(url=f"/repos/{repo_id}/graph", status_code=303)
