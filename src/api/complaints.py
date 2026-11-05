"""Complaints blueprint.

Phase 0 registers the routes so the shape of the API is visible, but the real
behaviour (storing complaints, queueing background work, resuming the graph)
arrives in Phase 6. For now each route returns HTTP 501 Not Implemented.
"""

from __future__ import annotations

import json

import azure.functions as func

bp = func.Blueprint()


def _not_implemented(route: str) -> func.HttpResponse:
    """Placeholder response until the route is built in a later phase."""
    body = json.dumps({"error": "not_implemented", "route": route, "phase": 6})
    return func.HttpResponse(body=body, status_code=501, mimetype="application/json")


@bp.route(route="complaints", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def create_complaint(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/complaints — accept a complaint and queue it (Phase 6)."""
    return _not_implemented("POST /api/complaints")


@bp.route(route="complaints/{id}", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def get_complaint(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/complaints/{id} — status, draft, citations, verdict (Phase 6)."""
    return _not_implemented("GET /api/complaints/{id}")


@bp.route(
    route="complaints/{id}/decision",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def decide_complaint(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/complaints/{id}/decision — human approval/override (Phase 6)."""
    return _not_implemented("POST /api/complaints/{id}/decision")


@bp.route(
    route="complaints/{id}/letter",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_letter(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/complaints/{id}/letter — final response letter (Phase 6)."""
    return _not_implemented("GET /api/complaints/{id}/letter")
