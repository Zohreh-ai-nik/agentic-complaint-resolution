"""Tests for the decision parser (Phase 1).

These use plain text fixtures, so no real PDFs or pdfplumber are needed.
"""

from __future__ import annotations

from src.data.parse import (
    build_decision,
    extract_outcome,
    split_sections,
)

SAMPLE = """DRN-1234567

The complaint
Mr A complains that his motor insurer declined his claim after an accident.

What happened
Mr A had a collision and claimed on his policy. The insurer declined, saying
the car was not roadworthy.

What I've decided - and why
I have considered the evidence. The insurer has not shown the fault caused the
accident, so declining the claim was unfair.

My final decision
My final decision is that I uphold this complaint. The insurer must pay the claim.
"""


def test_split_sections_finds_all_four() -> None:
    sections = split_sections(SAMPLE)
    assert sections["complaint"].startswith("Mr A complains")
    assert "collision" in sections["what_happened"]
    assert "considered the evidence" in sections["what_decided"]
    assert "uphold this complaint" in sections["final_decision"]


def test_split_sections_missing_section_is_empty() -> None:
    text = "The complaint\nSomething.\n\nMy final decision\nI do not uphold it."
    sections = split_sections(text)
    assert sections["complaint"] == "Something."
    assert sections["what_happened"] == ""
    assert sections["what_decided"] == ""
    assert "do not uphold" in sections["final_decision"]


def test_extract_outcome_upheld() -> None:
    assert extract_outcome("My final decision is that I uphold this complaint.") == "upheld"


def test_extract_outcome_not_upheld() -> None:
    assert extract_outcome("I do not uphold this complaint.") == "not_upheld"
    assert extract_outcome("I don't uphold this complaint.") == "not_upheld"


def test_extract_outcome_partly_upheld() -> None:
    assert extract_outcome("I partly uphold this complaint.") == "partly_upheld"


def test_extract_outcome_none_when_unclear() -> None:
    assert extract_outcome("") is None
    assert extract_outcome("Some unrelated text.") is None


def test_build_decision_flags_mismatch() -> None:
    listing = {"outcome_listing": "not_upheld", "date_listing": "12 January 2024"}
    decision = build_decision("DRN-1234567", SAMPLE, "data/raw/pdfs/DRN-1234567.pdf", listing)
    assert decision.outcome == "upheld"
    assert decision.outcome_listing == "not_upheld"
    assert decision.outcome_mismatch is True
    assert decision.date_listing == "12 January 2024"


def test_build_decision_no_mismatch_when_agree() -> None:
    listing = {"outcome_listing": "upheld", "date_listing": "12 January 2024"}
    decision = build_decision("DRN-1234567", SAMPLE, "x.pdf", listing)
    assert decision.outcome == "upheld"
    assert decision.outcome_mismatch is False
