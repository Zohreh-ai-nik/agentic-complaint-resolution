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


# ---------------------------------------------------------------------------
# Phase 1 — data models
# ---------------------------------------------------------------------------

# The three outcomes we recognise, used everywhere (parsing, splits, scoring).
OUTCOMES = ("upheld", "partly_upheld", "not_upheld")


class Decision(BaseModel):
    """One parsed Financial Ombudsman decision.

    Built from the decision PDF plus the listing row collected in index.csv.
    The four section fields come from the fixed headings in the PDF.
    """

    drn: str = Field(description="Decision reference number, e.g. 'DRN-1234567'.")
    outcome: str | None = Field(
        default=None,
        description="Outcome parsed from the final section: one of OUTCOMES, or None if unclear.",
    )
    outcome_listing: str | None = Field(
        default=None,
        description="Outcome recorded on the search listing, for cross-checking.",
    )
    outcome_mismatch: bool = Field(
        default=False,
        description="True when the parsed outcome disagrees with the listing outcome.",
    )
    date_listing: str | None = Field(
        default=None, description="Decision date from the listing (free text)."
    )
    complaint: str = Field(default="", description="Section: 'The complaint'.")
    what_happened: str = Field(default="", description="Section: 'What happened'.")
    what_decided: str = Field(
        default="", description="Section: \"What I've decided – and why\"."
    )
    final_decision: str = Field(default="", description="Section: 'My final decision'.")
    source_pdf: str = Field(description="Relative path to the source PDF.")
