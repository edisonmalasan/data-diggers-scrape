"""JobStreet deep pass: paginate each company's review pages 2..N until the
reviews go pre-2025 — reaching the 2025 reviews buried on deeper pages of
active employers (page 1 is covered by scrape_jobstreet.py).

Same contract gates as the base scraper (parse_review enforces them).
Writes to data/staging_jobstreet.csv with an IMMEDIATE per-company flush.
Resumes via .storage/jobstreet_deep_done.json.

Run AFTER scrape_jobstreet.py's current run has exited (shared staging file):
    python scripts/job_reviews/scrape_jobstreet_deep.py --limit 2000
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from scrape_jobstreet import (  # noqa: E402
    DATA_CSV, JS_PARSE, PRIORITY_RE, SLUGS_FILE, STORAGE, TOP_EMPLOYERS,
    append_rows, count_csv, parse_review,
)

DONE_FILE = STORAGE / "jobstreet_deep_done.json"
YEAR_RE = re.compile(r"20\d{2}")

# same industry set as scrape_jobstreet.main's rank tiers
ICT_IND = {
    "information-technology-services", "computer-software-n-networking",
    "telecommunications-n-internet-service-providers",
    "business-support-services", "employment-services",
    "facilities-management-n-outsourced-services",
    "banking-n-credit", "financial-investment-services", "insurance",
    "consulting-services", "online-media-n-ecommerce",
}


def load_deep_done() -> set[str]:
    if DONE_FILE.exists():
        return set(json.loads(DONE_FILE.read_text(encoding="utf-8")))
    return set()


def save_deep_done(done: set[str]) -> None:
    DONE_FILE.write_text(json.dumps(sorted(done), indent=0), encoding="utf-8")


def page_max_year(revs: list[dict]) -> int:
    """Max 4-digit year appearing in any review's text/lines on this page."""
    best = 0
    for r in revs:
        blob = (r.get("text") or "") + " " + " ".join(r.get("lines") or [])
        for m in YEAR_RE.finditer(blob):
            y = int(m.group(0))
            if 2000 <= y <= 2030 and y > best:
                best = y
    return best


def rank(s: dict) -> int:
    """Mirror of scrape_jobstreet.main's rank (same slug-dict fields)."""
    slug = s["slug"]
    tech = bool(PRIORITY_RE.search(slug))
    recent = s.get("ts", "") >= "2025"
    ind = s.get("ind") or ""
    if TOP_EMPLOYERS.match(slug):
        return 0
    if s.get("rev") is False:
        return 9
    if s.get("rev"):
        if ind in ICT_IND:
            return 1
        if tech:
            return 2
        return 3
    if tech and recent:
        return 4
    return 5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2000,
                    help="max companies to deep-page this run (default 2000)")
    ap.add_argument("--max-pages", type=int, default=10,
                    help="deepest page per company (default 10)")
    ap.add_argument("--sleep", type=float, default=1.8,
                    help="polite delay between page fetches")
    args = ap.parse_args()

    slugs = json.loads(SLUGS_FILE.read_text(encoding="utf-8"))
    done = load_deep_done()
    todo_rows = sorted((s for s in slugs if s["slug"] not in done),
                       key=rank)
    todo_rows = [s for s in todo_rows if rank(s) != 9]
    todo = [s["slug"] for s in todo_rows][: args.limit]
    print(f"[deep] slugs={len(slugs)} done={len(done)} "
          f"todo_this_run={len(todo)} rows_now={count_csv()}", flush=True)
    if not todo:
        print("[deep] nothing to do")
        return 0

    from playwright.sync_api import sync_playwright

    now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731
    stats = {"pages": 0, "kept": 0, "companies": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        ctx = browser.new_context(locale="en-US")
        page = ctx.new_page()
        try:
            for i, slug in enumerate(todo, 1):
                base = f"https://ph.jobstreet.com/companies/{slug}/reviews"
                kept_rows: list[dict] = []
                prev_sig: str | None = None
                stopped = ""
                try:
                    for pno in range(2, args.max_pages + 1):
                        url = f"{base}?page={pno}"
                        page.goto(url, timeout=45000,
                                  wait_until="domcontentloaded")
                        try:
                            page.wait_for_function(
                                "document.body.innerText.includes('The good things') ||"
                                " document.body.innerText.includes('Write a review')",
                                timeout=12000)
                        except Exception:
                            pass
                        page.wait_for_timeout(700)
                        title = page.title().lower()
                        body = page.inner_text("body")
                        if "just a moment" in title or \
                                "security verification" in body[:500].lower():
                            print(f"[deep {i}/{len(todo)}] {slug}: "
                                  "CLOUDFLARE -> waiting")
                            page.wait_for_timeout(15000)
                            page.reload()
                            page.wait_for_timeout(5000)
                        data = page.evaluate(JS_PARSE)
                        revs = data.get("reviews") or []
                        stats["pages"] += 1
                        if not revs:
                            stopped = "exhausted"
                            break
                        sig = (revs[0].get("text") or "")[:120]
                        if sig == prev_sig:
                            stopped = "pagination-noop"
                            break
                        prev_sig = sig
                        company = data.get("company") or slug
                        for raw in revs:
                            row = parse_review(raw, company, url, now_iso())
                            if row:
                                kept_rows.append(row)
                                stats["kept"] += 1
                        if page_max_year(revs) < 2025:
                            stopped = "pre-2025"
                            break
                        time.sleep(args.sleep)
                except KeyboardInterrupt:
                    raise
                except Exception as e:  # noqa: BLE001 — keep the pass alive
                    import traceback
                    traceback.print_exc()
                    stopped = f"error:{type(e).__name__}"
                finally:
                    if kept_rows:
                        add, skip = append_rows(kept_rows)
                        print(f"[deep {i}/{len(todo)}] {slug}: "
                              f"kept={len(kept_rows)} flushed {add} "
                              f"(+{skip} dup) stop={stopped or 'max-pages'}")
                    else:
                        print(f"[deep {i}/{len(todo)}] {slug}: kept=0 "
                              f"stop={stopped or 'max-pages'}")
                    done.add(slug)
                    save_deep_done(done)
                    time.sleep(args.sleep)
                stats["companies"] += 1
        except KeyboardInterrupt:
            print("\n[deep] interrupted — state saved")
        except Exception:
            import traceback
            traceback.print_exc()
            print("[deep] FATAL — done-set saved per company")
        finally:
            browser.close()

    print(f"[deep] DONE companies={stats['companies']} pages={stats['pages']} "
          f"kept={stats['kept']} rows_now={count_csv()} -> {DATA_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
