"""Tests for the collector's HTML parsing (Phase 1).

These use a small HTML fixture shaped like the live search results, so no
network calls are made. They guard two things that broke before:
  - the decision link is relative ("decision/DRN-xxx.pdf", no leading slash);
  - the date appears AFTER the link, not before (so dates must not shift).
"""

from __future__ import annotations

from src.data.collect import parse_results

# Two result blocks shaped like the real page: relative link, then heading + date.
SAMPLE_HTML = """
<p role="status">Your search returned 8435 results</p>
<ul class="search-results">
  <li>
    <a href="decision/DRN-6621070.pdf" class="search-result" target="_blank">
      <h3>Decision Reference DRN-6621070</h3>
      <div class="date">15 Sep 2026</div>
      <p>The complaint about a motor policy...</p>
    </a>
  </li>
  <li>
    <a href="decision/DRN-6524487.pdf" class="search-result" target="_blank">
      <h3>Decision Reference DRN-6524487</h3>
      <div class="date">14 Sep 2026</div>
      <p>Another motor complaint...</p>
    </a>
  </li>
</ul>
"""


def test_parse_results_finds_relative_links() -> None:
    results = parse_results(SAMPLE_HTML)
    drns = [drn for drn, _ in results]
    assert drns == ["DRN-6621070", "DRN-6524487"]


def test_parse_results_dates_are_not_shifted() -> None:
    results = parse_results(SAMPLE_HTML)
    assert dict(results) == {
        "DRN-6621070": "15 Sep 2026",
        "DRN-6524487": "14 Sep 2026",
    }


def test_parse_results_handles_absolute_links_too() -> None:
    html = '<a href="/decision/DRN-1111111.pdf"><h3>DRN-1111111</h3> 1 Jan 2025</a>'
    results = parse_results(html)
    assert results == [("DRN-1111111", "1 Jan 2025")]


def test_parse_results_deduplicates() -> None:
    html = SAMPLE_HTML + SAMPLE_HTML
    results = parse_results(html)
    drns = [drn for drn, _ in results]
    assert drns == ["DRN-6621070", "DRN-6524487"]
