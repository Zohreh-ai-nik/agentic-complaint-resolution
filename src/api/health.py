"""Health blueprint: GET /api/health.

Returns a small JSON payload so load balancers, pipelines and humans can check
the app is alive and see which version is deployed.
"""

from __future__ import annotations

import json

import azure.functions as func

from src.schemas import HealthResponse
from src.settings import app_env, app_version

bp = func.Blueprint()


def health_payload() -> HealthResponse:
    """Build the health response. Pure function, easy to unit-test."""
    return HealthResponse(status="ok", version=app_version(), env=app_env())


@bp.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger for GET /api/health."""
    payload = health_payload()
    return func.HttpResponse(
        body=json.dumps(payload.model_dump()),
        status_code=200,
        mimetype="application/json",
    )
