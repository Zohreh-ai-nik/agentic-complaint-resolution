"""Tests for the health endpoint (Phase 0)."""

from __future__ import annotations

import json

import azure.functions as func

from src.api.health import health, health_payload


def test_health_payload_is_ok() -> None:
    """The pure payload builder reports status 'ok' and a version."""
    payload = health_payload()
    assert payload.status == "ok"
    assert payload.version
    assert payload.env


def test_health_route_returns_200() -> None:
    """The HTTP trigger returns 200 with a JSON body of status 'ok'."""
    req = func.HttpRequest(method="GET", url="/api/health", body=b"", params={})
    resp = health(req)
    assert resp.status_code == 200
    data = json.loads(resp.get_body())
    assert data["status"] == "ok"
    assert "version" in data
    assert "env" in data
