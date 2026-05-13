# backend/routers/html.py
"""HTML 応答（htmx 向け）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from backend import paths, state_store
from backend.db import get_session
from backend.exceptions import CommitNotFoundError, RepositoryNotFoundError
from backend.jinja import templates
from backend.models import Commit, Repository
from backend.repositories import commit_repo, repository_repo, tag_repo
from backend.services import graph_service
from backend.services.graph_models import GraphResult
from backend.validation import parse_commit_hash, parse_repo_id

router = APIRouter(tags=["html"])
_logger = logging.getLogger(__name__)


def _save_state_and_fetch_detail(
    session: Session,
    rid: str,
    show_remote: bool,
    show_tags: bool,
    active_commit: str | None,
) -> tuple[Commit | None, list[str]]:
    """グラフ状態を保存し active_commit の詳細を返す。"""
    state_store.update(
        paths.window_state_path(),
        repo_id=rid,
        show_remote=show_remote,
        show_tags=show_tags,
    )
    # active_commit が有効なコミットハッシュならその詳細を返す
    if active_commit is None:
        return None, []
    try:
        ch = parse_commit_hash(active_commit)
    except Exception:
        return None, []
    row = commit_repo.get_commit(session, rid, ch)
    if row is None:
        return None, []
    return row, tag_repo.get_tags_for_commit(session, rid, ch)


def _build_graph_context(
    rid: str,
    rec: Repository,
    result: GraphResult,
    show_remote: bool,
    show_tags: bool,
    active_commit: str | None,
    detail_commit: Commit | None,
    detail_tags: list[str],
    session: Session,
) -> dict:
    """グラフページのテンプレートコンテキストを構築する。"""
    return {
        "repo_id": rid,
        "repo_name": rec.name,
        "nodes": result.nodes,
        "edges": result.edges,
        "branch_headers": result.branch_headers,
        "svg_width": result.canvas_width,
        "svg_height": result.canvas_height,
        "repos": repository_repo.list_repositories(session),
        "current_repo_id": rid,
        "show_remote": show_remote,
        "show_tags": show_tags,
        "active_commit": active_commit,
        "active_detail_commit": detail_commit,
        "active_detail_tags": detail_tags,
    }


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
    show_remote: bool = True,
    show_tags: bool = True,
    active_commit: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """ブランチグラフ画面を返す。"""
    rid = parse_repo_id(repo_id)
    rec = repository_repo.get_repository(session, rid)
    if rec is None:
        raise RepositoryNotFoundError
    result = graph_service.sync_and_build(
        session, rid, rec.path, show_remote=show_remote, show_tags=show_tags
    )
    detail_commit, detail_tags = _save_state_and_fetch_detail(
        session, rid, show_remote, show_tags, active_commit
    )
    context = _build_graph_context(
        rid,
        rec,
        result,
        show_remote,
        show_tags,
        active_commit,
        detail_commit,
        detail_tags,
        session,
    )
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
    state_store.update(paths.window_state_path(), commit_hash=ch)
    return templates.TemplateResponse(
        request, "partials/detail.html", {"commit": row, "tags": tags}
    )
