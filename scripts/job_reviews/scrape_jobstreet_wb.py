"""Scrape 2026 Wayback captures of JobStreet review pages -> CSV.

Archived captures freeze the '30 most recent reviews' as of capture time, so a
page captured mid-2026 holds 2026-H1 reviews that have since scrolled off the
live page 1. Public archive (DATA_CONTRACT rule 9); same parser + gates as the
live JobStreet scraper, but static HTML -> BeautifulSoup instead of Playwright.

Run:  python scripts/job_reviews/scrape_jobstreet_wb.py [--target 900] [--limit 400]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scrape_jobstreet import DATE_RE, append_rows, count_csv, parse_review

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"
URLS_FILE = STORAGE / "jobstreet_wb.json"
DONE_FILE = STORAGE / "jobstreet_wb_done.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}


def load_done() -> set[str]:
    return set(json.loads(DONE_FILE.read_text(encoding="utf-8"))) if DONE_FILE.exists() else set()


def save_done(done: set[str]) -> None:
    DONE_FILE.write_text(json.dumps(sorted(done), indent=0), encoding="utf-8")


def lines0(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split("\n") if x.strip()]


def parse_page(html: str, url: str) -> tuple[str, list[dict]]:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    m = re.search(r"Reviews\s+(.+?)\s+employee ratings", title) or \
        re.search(r"^About\s+(.+?)\s+Company", title)
    company = m.group(1).strip() if m else "Unknown"

    labels = [e for e in soup.find_all(["span", "div"])
              if e.get_text(strip=True) == "The good things"]
    out, seen = [], set()
    for lab in labels:
        node, cont = lab, None
        for _ in range(10):
            if node is None:
                break
            t = node.get_text(" ", strip=True)
            if "Helpful" in t and DATE_RE.search(t):
                cont = node
                break
            node = node.parent
        if cont is None or id(cont) in seen:
            continue
        seen.add(id(cont))
        rating = ""
        r_el = cont.find(attrs={"aria-label": re.compile("out of 5")})
        if r_el:
            mm = re.search(r"([\d.]+)\s*out of", r_el.get("aria-label", ""))
            rating = mm.group(1) if mm else ""
        text = cont.get_text("\n")
        out.append({"rating": rating, "text": text, "lines": lines0(text)})
    return company, out


def fetch(u: str, timeout: int = 90) -> str | None:
    """Returns HTML, '' for definitive misses (404/410/403), None for
    transient failure after retries (caller must NOT mark done)."""
    for attempt in range(4):
        try:
            r = requests.get(u, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            if r.status_code == 429:
                wait = 45 * (attempt + 1)
                print(f"    429; sleeping {wait}s")
                time.sleep(wait)
                continue
            if r.status_code in (403, 404, 410):
                return ""
            time.sleep(8)
        except requests.RequestException as e:
            print(f"    fetch error: {e}")
            time.sleep(8 + attempt * 6)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=900)
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--sleep", type=float, default=1.2)
    args = ap.parse_args()

    if not URLS_FILE.exists():
        print("no jobstreet_wb.json yet — run enum_jobstreet_wb.py first")
        return 1
    items = json.loads(URLS_FILE.read_text(encoding="utf-8"))
    done = load_done()
    # newest captures first: their page-1 windows sit deepest inside 2026
    todo = sorted((i for i in items if f"{i['ts']}|{i['url']}" not in done),
                  key=lambda i: i["ts"], reverse=True)[: args.limit]
    print(f"js-wb urls={len(items)} done={len(done)} todo={len(todo)} "
          f"rows_now={count_csv()} target={args.target}")

    rows: list[dict] = []
    stats = {"ok": 0, "reviews": 0, "kept": 0, "miss": 0}
    for n, item in enumerate(todo, 1):
        if count_csv() + len(rows) >= args.target:
            print(f"target {args.target} reached")
            break
        orig, ts = item["url"], item["ts"]
        snap = f"https://web.archive.org/web/{ts}id_/{orig}"
        key = f"{ts}|{orig}"
        mark_done = False  # becomes True only on definitive outcomes
        try:
            html = fetch(snap)
            if html is None:
                stats["miss"] += 1          # transient — will retry next run
            elif html == "":
                stats["miss"] += 1          # definitive 404/410/403
                mark_done = True
            else:
                mark_done = True
                company, reviews = parse_page(html, orig)
                now = datetime.now(timezone.utc).isoformat()
                kept = 0
                for raw in reviews:
                    row = parse_review(raw, company, orig, now)
                    if row:
                        rows.append(row)
                        kept += 1
                stats["ok"] += 1
                stats["reviews"] += len(reviews)
                stats["kept"] += kept
                if n % 10 == 0 or kept:
                    print(f"[{n}/{len(todo)}] {company[:28]}: reviews={len(reviews)} "
                          f"kept={kept} (new={len(rows)})")
        except KeyboardInterrupt:
            break
        except Exception as e:  # noqa: BLE001
            print(f"[{n}/{len(todo)}] ERROR {orig[:70]}: {type(e).__name__} {e}")
        finally:
            if mark_done:
                done.add(key)
                save_done(done)
            time.sleep(args.sleep + random.uniform(0, 0.4))

    added, skipped = append_rows(rows)
    print(f"DONE ok={stats['ok']} reviews={stats['reviews']} kept={stats['kept']} "
          f"miss={stats['miss']} -> added={added} deduped={skipped} "
          f"rows_now={count_csv()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
