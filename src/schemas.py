"""Pydantic models shared across the app.

Phase 0 only needs the health response. More models (Complaint, Decision,
GraphState, Citation, CheckerVerdict, Letter) are added in later phases.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Payload returned by GET /api/health."""

    status: str = Field(description="'ok' when the app is healthy.")
    version: str = Field(description="Application version.")
    env: str = Field(description="Deployment environment, e.g. 'local' or 'uat'.")
