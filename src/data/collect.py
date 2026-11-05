"""
Collect Financial Ombudsman decisions (public PDFs), slowly and politely.

Three commands:
  index     read a filtered search page by page and list the decisions in data/raw/index.csv
  download  download the PDFs listed in index.csv into data/raw/pdfs/
  stats     show what you have so far

Usage (run from the repo folder):
  python -m src.data.collect index --url "<search URL with Upheld ticked>" --label upheld --max 30
  python -m src.data.collect index --url "<search URL with Not upheld ticked>" --label not_upheld --max 30
  python -m src.data.collect download --max 60
  python -m src.data.collect stats

Both index and download skip what you already have, so you can stop and re-run at any time.
"""

import argparse
import csv
import os
import random
import re
import time
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

try:  # optional: read CONTACT_EMAIL from a .env file
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE = "https://www.financial-ombudsman.org.uk"
RAW = Path("data/raw")
INDEX = RAW / "index.csv"
PDF_DIR = RAW / "pdfs"
COLUMNS = ["drn", "outcome_listing", "date_listing", "pdf_url", "source_url", "collected_at"]
PAGE_SIZE = 10          # the search shows 10 decisions per page
MIN_DELAY = 3.0         # never faster than one request every 3 seconds

DRN_LINK = re.compile(r"/decision/(DRN-\d+)\.pdf", re.IGNORECASE)
DATE = re.compile(r"\b(\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4})\b")
TAG = re.compile(r"<[^>]+>")


# ---------- HTTP ----------

def make_session() -> requests.Session:
    email = os.environ.get("CONTACT_EMAIL", "").strip()
    agent = "ComplaintDesk personal research project"
    if email:
        agent += f" ({email})"
    s = requests.Session()
    s.headers["User-Agent"] = agent
    return s


def polite_get(s: requests.Session, url: str, delay: float, tries: int = 4):
    """GET with retries and exponential back-off (with jitter). Returns None if it keeps failing."""
    for attempt in range(1, tries + 1):
        try:
            r = s.get(url, timeout=60)
        except requests.RequestException as e:
            wait = delay * 2 ** attempt + random.uniform(0, 1)
            print(f"  network error ({e.__class__.__name__}); retry in {wait:.0f}s")
            time.sleep(wait)
            continue
        if r.status_code == 200:
            return r
        if r.status_code in (429, 500, 502, 503, 504):
            retry_after = r.headers.get("Retry-After", "")
            wait = float(retry_after) if retry_after.isdigit() else delay * 2 ** attempt + random.uniform(0, 1)
            print(f"  HTTP {r.status_code}; retry in {wait:.0f}s")
            time.sleep(wait)
            continue
        print(f"  HTTP {r.status_code} for {url}; skipped")
        return None
    print(f"  gave up on {url}")
    return None


def pause(delay: float) -> None:
    time.sleep(delay + random.uniform(0, 1))


# ---------- index.csv ----------

def load_index() -> dict[str, dict]:
    if not INDEX.exists():
        return {}
    with INDEX.open(newline="", encoding="utf-8") as f:
        return {row["drn"]: row for row in csv.DictReader(f)}


def append_rows(rows: list[dict]) -> None:
    if not rows:
        return
    is_new = not INDEX.exists()
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    with INDEX.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerows(rows)


def with_start(url: str, start: int) -> str:
    """Return the same search URL with Start=<start> (the page offset)."""
    parts = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() != "start"]
    query.append(("Start", str(start)))
    return urlunparse(parts._replace(query=urlencode(query)))


def parse_results(html: str) -> list[tuple[str, str]]:
    """Find decisions on one search page: [(DRN, date)] in page order.

    The DRN comes from the PDF link, which is reliable. The date is best effort:
    the nearest date in the text just before the link (may be blank)."""
    found, seen = [], set()
    for m in DRN_LINK.finditer(html):
        drn = m.group(1).upper()
        if drn in seen:
            continue
        seen.add(drn)
        before = TAG.sub(" ", unescape(html[max(0, m.start() - 2000): m.start()]))
        dates = DATE.findall(before)
        found.append((drn, dates[-1] if dates else ""))
    return found


# ---------- commands ----------

def cmd_index(args) -> None:
    delay = max(args.delay, MIN_DELAY)
    s = make_session()
    known = load_index()
    added, start = 0, args.start
    while added < args.max:
        url = with_start(args.url, start)
        print(f"search page Start={start}")
        r = polite_get(s, url, delay)
        if r is None:
            break
        results = parse_results(r.text)
        if not results:
            print("  no decisions found on this page; stopping")
            break
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = []
        for drn, date in results:
            if drn in known or added + len(rows) >= args.max:
                continue
            row = {
                "drn": drn,
                "outcome_listing": args.label,
                "date_listing": date,
                "pdf_url": f"{BASE}/decision/{drn}.pdf",
                "source_url": url,
                "collected_at": now,
            }
            rows.append(row)
            known[drn] = row
        append_rows(rows)
        added += len(rows)
        print(f"  +{len(rows)} new (this run: {added})")
        start += PAGE_SIZE
        pause(delay)
    print(f"done: {added} new decisions added to {INDEX}")


def cmd_download(args) -> None:
    delay = max(args.delay, MIN_DELAY)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    s = make_session()
    done = 0
    for row in load_index().values():
        if done >= args.max:
            break
        path = PDF_DIR / f"{row['drn']}.pdf"
        if path.exists() and path.stat().st_size > 0:
            continue
        r = polite_get(s, row["pdf_url"], delay)
        if r is None or not r.content.startswith(b"%PDF"):
            print(f"  {row['drn']}: not a PDF, skipped")
            pause(delay)
            continue
        tmp = path.with_suffix(".part")
        tmp.write_bytes(r.content)
        tmp.replace(path)           # only complete files get the .pdf name
        done += 1
        print(f"  saved {path.name} ({len(r.content) // 1024} KB) [{done}/{args.max}]")
        pause(delay)
    print(f"done: {done} PDFs downloaded this run")


def cmd_stats(_args) -> None:
    rows = list(load_index().values())
    have = {p.stem for p in PDF_DIR.glob("*.pdf")} if PDF_DIR.exists() else set()
    print(f"decisions in index: {len(rows)}")
    print(f"PDFs downloaded:    {len(have)}")
    print("by outcome:", dict(Counter(r["outcome_listing"] for r in rows)))
    years = Counter(r["date_listing"][-4:] for r in rows if r["date_listing"])
    print("by year:", dict(sorted(years.items())))
    print(f"missing dates:      {sum(1 for r in rows if not r['date_listing'])}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("index", help="list decisions from a filtered search URL")
    pi.add_argument("--url", required=True, help="search URL copied from the browser, with your filters")
    pi.add_argument("--label", required=True, choices=["upheld", "not_upheld"], help="the outcome you filtered on")
    pi.add_argument("--max", type=int, default=50)
    pi.add_argument("--start", type=int, default=0, help="page offset to start from (0, 10, 20...)")
    pi.add_argument("--delay", type=float, default=4.0)
    pi.set_defaults(func=cmd_index)

    pd = sub.add_parser("download", help="download PDFs listed in index.csv")
    pd.add_argument("--max", type=int, default=50)
    pd.add_argument("--delay", type=float, default=4.0)
    pd.set_defaults(func=cmd_download)

    ps = sub.add_parser("stats", help="show counts")
    ps.set_defaults(func=cmd_stats)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
