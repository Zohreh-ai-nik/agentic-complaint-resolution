"""Tests for the train/dev/library splitter (Phase 1)."""

from __future__ import annotations

from datetime import date

from src.data.split import assign_splits, parse_date


def test_parse_date_valid() -> None:
    assert parse_date("12 January 2024") == date(2024, 1, 12)
    assert parse_date("Decision issued 3 Mar 2022") == date(2022, 3, 3)


def test_parse_date_invalid() -> None:
    assert parse_date("") is None
    assert parse_date(None) is None
    assert parse_date("no date here") is None


def _records(n: int, outcome: str, start_year: int) -> list[dict]:
    """Make n records for one outcome, each a year apart (newest = highest year)."""
    return [
        {"drn": f"{outcome}-{i}", "outcome": outcome, "_date": date(start_year + i, 1, 1)}
        for i in range(n)
    ]


def test_assign_splits_balanced_and_newest_first() -> None:
    # 10 upheld + 10 not_upheld. Ask for test=4 (2 per class), dev=4 (2 per class).
    records = _records(10, "upheld", 2000) + _records(10, "not_upheld", 2000)
    assignment = assign_splits(records, test_size=4, dev_size=4)

    test = [drn for drn, s in assignment.items() if s == "test"]
    dev = [drn for drn, s in assignment.items() if s == "dev"]
    library = [drn for drn, s in assignment.items() if s == "library"]

    # 2 per class in test and dev; the rest in library.
    assert len(test) == 4
    assert len(dev) == 4
    assert len(library) == 12

    # Test set must hold the NEWEST (highest index -> highest year) of each class.
    assert "upheld-9" in test and "upheld-8" in test
    assert "not_upheld-9" in test and "not_upheld-8" in test


def test_assign_splits_every_drn_assigned_once() -> None:
    records = _records(5, "upheld", 2010) + _records(5, "not_upheld", 2010)
    assignment = assign_splits(records, test_size=2, dev_size=2)
    assert len(assignment) == 10
    assert set(assignment.values()) <= {"test", "dev", "library"}


def test_assign_splits_no_test_leaks_into_library() -> None:
    records = _records(6, "upheld", 2000)
    assignment = assign_splits(records, test_size=2, dev_size=2)
    test = {drn for drn, s in assignment.items() if s == "test"}
    library = {drn for drn, s in assignment.items() if s == "library"}
    assert test.isdisjoint(library)
