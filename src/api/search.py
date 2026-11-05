"""Search blueprint.

Direct search over one knowledge base (``decisions``, ``rules`` or ``policies``).
Useful for debugging retrieval and, later, as the basis for MCP tools.
The real implementation lands in Phase 3; Phase 0 returns 501.
"""

from __future__ import annotations

import json

import azure.functions as func

bp = func.Blueprint()


@bp.route(route="search/{source}", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def search(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/search/{source} — hybrid search over a knowledge base (Phase 3)."""
    body = json.dumps(
        {"error": "not_implemented", "route": "POST /api/search/{source}", "phase": 3}
    )
    return func.HttpResponse(body=body, status_code=501, mimetype="application/json")
