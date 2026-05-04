# backend/routers/api.py
"""登録などの HTTP API。"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Annotated

import pygit2
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backend.db import get_session
from backend.exceptions import (
    DirectoryNotFoundError,
    GitOpenError,
    RepositoryAlreadyRegisteredError,
)
from backend.repositories import repository_repo
from backend.repositories.git_repo import open_repository
from backend.services.watch_service import WatchService

router = APIRouter(tags=["api"])
_logger = logging.getLogger(__name__)


def _get_watch_service(request: Request) -> WatchService | None:
    """app.state から WatchService を取り出す。lifespan 未起動時は None。"""
    return getattr(request.app.state, "watch_service", None)


@router.post("/api/repos")
async def register_repository(
    request: Request,
    path: Annotated[str, Form()],
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """フォルダパスからリポジトリを登録し、グラフ画面へリダイレクトする。"""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise DirectoryNotFoundError
    try:
        open_repository(str(resolved))
    except pygit2.GitError as exc:
        raise GitOpenError from exc
    repo_id = str(uuid.uuid4())
    existing = repository_repo.get_repository_by_path(session, str(resolved))
    _logger.info("リポジトリ登録: path=%s 既存=%s", resolved, existing is not None)
    watch_svc = _get_watch_service(request)
    if existing is not None:
        if watch_svc is not None:
            watch_svc.watch(existing.id, existing.path)
        return RedirectResponse(url=f"/repos/{existing.id}/graph", status_code=303)
    try:
        repository_repo.insert_repository(session, repo_id, str(resolved), resolved.name)
    except IntegrityError as exc:
        raise RepositoryAlreadyRegisteredError from exc
    if watch_svc is not None:
        watch_svc.watch(repo_id, str(resolved))
    return RedirectResponse(url=f"/repos/{repo_id}/graph", status_code=303)
