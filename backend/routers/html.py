# backend/routers/html.py
"""HTML 応答（htmx 向け）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from backend.db import get_session
from backend.exceptions import CommitNotFoundError, RepositoryNotFoundError
from backend.jinja import templates
from backend.repositories import commit_repo, repository_repo, tag_repo
from backend.services import graph_service
from backend.validation import parse_commit_hash, parse_repo_id

router = APIRouter(tags=["html"])
_logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse)
async def welcome(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ウェルカム画面を返す。"""
    repos = repository_repo.list_repositories(session)
    return templates.TemplateResponse(
        request, "welcome.html", {"repos": repos, "current_repo_id": None}
    )


@router.get("/repos/{repo_id}/graph", response_class=HTMLResponse)
async def graph_page(
    request: Request,
    repo_id: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ブランチグラフ画面を返す。"""
    rid = parse_repo_id(repo_id)
    rec = repository_repo.get_repository(session, rid)
    if rec is None:
        raise RepositoryNotFoundError
    result = graph_service.sync_and_build(session, rid, rec.path)
    context: dict = {
        "repo_id": rid,
        "repo_name": rec.name,
        "nodes": result.nodes,
        "edges": result.edges,
        "branch_headers": result.branch_headers,
        "svg_width": result.canvas_width,
        "svg_height": result.canvas_height,
        "repos": repository_repo.list_repositories(session),
        "current_repo_id": rid,
    }
    return templates.TemplateResponse(request, "graph.html", context)


@router.get(
    "/repos/{repo_id}/commits/{commit_hash}/detail",
    response_class=HTMLResponse,
)
async def commit_detail(
    request: Request,
    repo_id: str,
    commit_hash: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """コミット詳細の HTML 断片を返す（htmx 用）。"""
    rid = parse_repo_id(repo_id)
    ch = parse_commit_hash(commit_hash)
    row = commit_repo.get_commit(session, rid, ch)
    if row is None:
        raise CommitNotFoundError
    tags = tag_repo.get_tags_for_commit(session, rid, ch)
    return templates.TemplateResponse(
        request, "partials/detail.html", {"commit": row, "tags": tags}
    )
