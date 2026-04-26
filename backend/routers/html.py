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
from backend.models import Repository
from backend.repositories import cache_repo
from backend.services import graph_layout, sync_service
from backend.validation import parse_commit_hash, parse_repo_id

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["html"])


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


def _build_graph_context(
    rid: str,
    rec: Repository,
    nodes: list,
    edges: list,
    branch_lanes: list,
) -> dict:
    """グラフ画面のテンプレートコンテキストを構築する。

    Args:
        rid: リポジトリ ID。
        rec: リポジトリレコード。
        nodes: レイアウト済みノード一覧。
        edges: エッジ一覧。
        branch_lanes: ブランチレーン一覧。

    Returns:
        Jinja2 テンプレートに渡すコンテキスト辞書。
    """
    from backend.services.graph_layout import LANE_COLORS, ROW_SPACING, build_edge_segments

    max_lane = max((bl.lane for bl in branch_lanes), default=0)
    svg_width = max(320, max_lane * 70 + 300)
    svg_height = 80.0 + max(len(nodes), 1) * ROW_SPACING
    return {
        "repo_id": rid,
        "repo_name": rec.name,
        "nodes": nodes,
        "edge_segments": build_edge_segments(nodes, edges),
        "branch_lanes": branch_lanes,
        "position_by_hash": {n.commit.hash: n for n in nodes},
        "svg_width": svg_width,
        "svg_height": svg_height,
        "lane_colors": LANE_COLORS,
        "row_spacing": ROW_SPACING,
    }


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
    branches = cache_repo.list_branches(session, rid)
    nodes, edges, branch_lanes = graph_layout.build_multi_lane_layout(rows, parents, branches)
    context = _build_graph_context(rid, rec, nodes, edges, branch_lanes)
    context["repos"] = cache_repo.list_repositories(session)
    context["current_repo_id"] = rid
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
    return templates.TemplateResponse(request, "partials/detail.html", {"commit": row})
