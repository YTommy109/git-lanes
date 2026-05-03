# backend/routers/html.py
"""HTML 応答（htmx 向け）。"""

from __future__ import annotations

import logging
from pathlib import Path

import pygit2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from backend.db import get_session
from backend.repositories import cache_repo
from backend.services import grid_builder, sync_service
from backend.validation import parse_commit_hash, parse_repo_id

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["html"])
_logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse)
async def welcome(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ウェルカム画面を返す。"""
    repos = cache_repo.list_repositories(session)
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
    rec = cache_repo.get_repository(session, rid)
    if rec is None:
        raise HTTPException(status_code=404, detail="リポジトリが見つかりません")
    try:
        sync_service.sync_repository(session, rid, rec.path)
    except pygit2.GitError as exc:
        raise HTTPException(status_code=400, detail="Git リポジトリを開けません") from exc
    rows = cache_repo.list_all_commits(session, rid)
    parents = cache_repo.parents_by_child(session, [r.hash for r in rows])
    branches = cache_repo.list_branches(session, rid)
    tags = cache_repo.list_tags(session, rid)
    _logger.debug("グラフ描画: repo_id=%s commits=%d branches=%d", rid, len(rows), len(branches))
    result = grid_builder.build_grid(rows, parents, branches, tags, rec.cached_head)
    context: dict = {
        "repo_id": rid,
        "repo_name": rec.name,
        "nodes": result.nodes,
        "edges": result.edges,
        "branch_headers": result.branch_headers,
        "svg_width": result.canvas_width,
        "svg_height": result.canvas_height,
        "repos": cache_repo.list_repositories(session),
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
    row = cache_repo.get_commit(session, rid, ch)
    if row is None:
        raise HTTPException(status_code=404, detail="コミットが見つかりません")
    tags = cache_repo.get_tags_for_commit(session, rid, ch)
    return templates.TemplateResponse(
        request, "partials/detail.html", {"commit": row, "tags": tags}
    )
