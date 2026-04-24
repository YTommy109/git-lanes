# backend/routers/html.py
"""HTML 応答（htmx 向け）。"""

from __future__ import annotations

from pathlib import Path

import pygit2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from backend.db import get_session
from backend.repositories import cache_repo
from backend.services import graph_layout, sync_service
from backend.validation import parse_commit_hash, parse_repo_id

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["html"])


@router.get("/", response_class=HTMLResponse)
async def welcome(request: Request) -> HTMLResponse:
    """ウェルカム画面を返す。"""
    return templates.TemplateResponse(request, "welcome.html", {})


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
    rows = cache_repo.list_recent_commits(session, rid, 50)
    parents = cache_repo.parents_by_child(session, [r.hash for r in rows])
    nodes, edges = graph_layout.build_single_lane_layout(rows, parents)
    position_by_hash = {n.commit.hash: n for n in nodes}
    row_spacing = 52.0
    svg_height = 80.0 + max(len(nodes), 1) * row_spacing
    return templates.TemplateResponse(
        request,
        "graph.html",
        {
            "repo_id": rid,
            "repo_name": rec.name,
            "nodes": nodes,
            "edges": edges,
            "position_by_hash": position_by_hash,
            "svg_height": svg_height,
        },
    )


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
    return templates.TemplateResponse(request, "partials/detail.html", {"commit": row})
