# backend/routers/api.py
"""登録などの HTTP API。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

import pygit2
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backend.db import get_session
from backend.repositories import cache_repo
from backend.repositories.git_repo import open_repository

router = APIRouter(tags=["api"])


@router.post("/api/repos")
async def register_repository(
    path: Annotated[str, Form()],
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """フォルダパスからリポジトリを登録し、グラフ画面へリダイレクトする。"""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="ディレクトリが存在しません")
    try:
        open_repository(str(resolved))
    except pygit2.GitError as exc:
        raise HTTPException(status_code=400, detail="Git リポジトリとして開けません") from exc
    repo_id = str(uuid.uuid4())
    existing = cache_repo.get_repository_by_path(session, str(resolved))
    if existing is not None:
        return RedirectResponse(url=f"/repos/{existing.id}/graph", status_code=303)
    try:
        cache_repo.insert_repository(session, repo_id, str(resolved), resolved.name)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="このパスは既に登録されています") from exc
    return RedirectResponse(url=f"/repos/{repo_id}/graph", status_code=303)
