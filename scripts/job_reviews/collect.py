"""Collect PH CS/IT employee reviews into ./data/job_reviews_raw.csv.

Run ON YOUR PC (not in the sandboxed agent).

RECOMMENDED (uses your current logged-in Chrome):

  1. Close Chrome completely.
  2. Reopen it with automation access enabled (keep this window open):
     & "C:/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA/Google/Chrome/User Data"
  3. Verify Indeed/Glassdoor show you logged in, then:
     python scripts/job_reviews/collect.py --check --cdp
     python scripts/job_reviews/collect.py --site indeed --max-pages 10 --cdp
     python scripts/job_reviews/to_markdown.py
     python scripts/job_reviews/validate.py

FALLBACK (fresh window + manual login, Indeed may block its auth flow):

  python scripts/job_reviews/login.py --site indeed
  python scripts/job_reviews/collect.py --check

Contract: docs/DATA_CONTRACT.md (14 columns, review_date in 2026, PH only,
CS/IT job_titles only, source_url per row, never fabricate).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = ROOT / "data" / "job_reviews_raw.csv"
SEED_FILE = Path(__file__).with_name("companies.seed.json")
STORAGE_DIR = Path(__file__).with_name(".storage")
CDP_DEFAULT_URL = "http://localhost:9222"

COLUMNS = [
    "review_id", "company_name", "job_title", "department",
    "seniority_level", "employment_status", "review_date", "rating",
    "review_text", "pros", "cons", "location",
    "source_platform", "source_url", "scraped_at",
]

# CS/IT-only gate: job_title must contain one of these (lowercase match).
CS_IT_KEYWORDS = [
    "software", "developer", "programmer", "engineer", "data ",
    "data analyst", "data scientist", "machine learning", " ai ",
    "it ", "information technology", "systems admin", "system admin",
    "network", "cybersecurity", "security analyst", "devops", "cloud",
    "web ", "mobile", "frontend", "front-end", "backend", "back-end",
    "full-stack", "full stack", "qa", "tester", "test engineer",
    "site reliability", "database", "dba", "ui/ux", "ux ", "support analyst",
    "helpdesk", "help desk", "technical support", "solutions architect",
    "systems analyst", "business analyst", "product analyst",
]

# PH gate: location text must mention one of these.
PH_KEYWORDS = [
    "philippines", "manila", "makati", "taguig", "bgc", "quezon city",
    "pasig", "mandaluyong", "cebu", "davao", "baguio", "iloilo",
    "clark", "alabang", "ortigas", "pasay", "paranaque", "cavite",
    "laguna", "batangas", "pampanga", "ncr", "metro manila",
]

# Card selectors per platform: (card, title, location, date, rating, text).
SELECTORS = {
    "indeed": ("div.empReview", ".jobTitle", ".companyLocation",
               ".reviewDate", ".ratingNumber", ".reviewText"),
    "glassdoor": ("div.empReview", ".p-t-XXSM", ".authorLocation",
                  "time", ".ratingNumber", ".reviewText"),
    "jobstreet": ("article.review-card", ".job-title", ".location",
                  ".review-date", ".rating", ".review-body"),
    "linkedin": ("article.post", ".job-title", ".location",
                 "time", "", ".post-text"),
}

# Real bot-block markers (navbar "sign in" text is NOT a block signal).
BLOCK_MARKERS = ["captcha", "datadome", "verify you are human",
                 "access denied", "unusual traffic", "are you a robot",
                 "prove you are human"]
LOGIN_MARKERS = ["log in to continue", "sign in to continue",
                 "create your account to continue", "join now to see"]


def is_cs_it(title: str) -> bool:
    t = f" {title.lower()} "
    return any(k in t for k in CS_IT_KEYWORDS)


def is_ph(location: str) -> bool:
    loc = location.lower()
    return any(k in loc for k in PH_KEYWORDS)


def make_id(company: str, title: str, date: str, text: str, url: str) -> str:
    raw = "|".join([company, title, date, text[:120], url]).encode()
    return "rv_" + hashlib.sha1(raw).hexdigest()[:12]


def norm_rating(raw: str | None) -> str:
    """Normalize '4.0/5', '4 out of 5', '80/100' to 1-5 float string; '' if unknown."""
    if not raw:
        return ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:/|out of\s+)?\s*(\d+)?", raw)
    if not m:
        return ""
    val, scale = float(m.group(1)), float(m.group(2) or 5)
    if scale == 100:  # e.g. 80/100 -> 4.0
        val = val / 20
    elif scale == 10:
        val = val / 2
    return f"{min(5.0, max(1.0, val)):.1f}"


def storage_for(platform: str) -> str | None:
    """Saved login session from login.py, if you created one for this site."""
    cand = STORAGE_DIR / f"{platform}.json"
    return str(cand) if cand.exists() else None


class Session:
    """Owns browser lifetime for fresh-window mode, or borrows your live
    Chrome in --cdp mode (never closes your browser)."""

    def __init__(self, p, cdp_url: str | None):
        self.cdp_url = cdp_url
        self._p = p
        self.browser = None
        self.ctx = None
        self._fresh: list[tuple] = []

    def context_for(self, platform: str):
        if self.cdp_url:
            if self.browser is None:
                self.browser = self._p.chromium.connect_over_cdp(self.cdp_url)
                ctxs = self.browser.contexts
                self.ctx = ctxs[0] if ctxs else self.browser.new_context()
                print("  (attached to YOUR running Chrome — your logins apply)")
            return self.ctx
        state = storage_for(platform)
        browser = self._p.chromium.launch(channel="chrome", headless=False)
        ctx = browser.new_context(storage_state=state) if state else browser.new_context()
        print(f"  (fresh window; session file: {state or 'none — run login.py --site ' + platform})")
        self._fresh.append((browser, ctx))
        return ctx

    def close(self):
        for browser, ctx in self._fresh:
            try:
                ctx.close()
                browser.close()
            except Exception:  # noqa: BLE001 — best effort teardown
                pass
        # CDP mode: leave the user's browser untouched.


def visible_text(page) -> tuple[str, str]:
    """(tab title, rendered body text). Rendered text only — raw HTML contains
    JS chunks mentioning 'captcha' that caused false BLOCKED verdicts."""
    try:
        title = page.title() or ""
    except Exception:  # noqa: BLE001
        title = ""
    try:
        body = (page.inner_text("body") or "").lower()
    except Exception:  # noqa: BLE001
        body = ""
    return title, body


def diagnose(page, platform: str) -> str:
    """Decide page state by content actually visible, not navbar wording."""
    title, body = visible_text(page)
    if title == "" and body == "":
        return "LOAD FAILED"
    card = SELECTORS.get(platform, SELECTORS["indeed"])[0]
    try:
        n = len(page.query_selector_all(card)) if card else 0
    except Exception:  # noqa: BLE001
        n = 0
    if n > 0:
        return f"OK ({n} review cards visible)"
    if any(k in body for k in BLOCK_MARKERS):
        return f"BLOCKED (bot check / captcha) [tab: {title[:60]}]"
    if any(k in body for k in LOGIN_MARKERS):
        return f"LOGIN WALL [tab: {title[:60]}]"
    return f"NO CARDS (tab: {title[:60]} | text: {body[:150]})"


def check_mode(cdp_url: str | None) -> int:
    """No scraping: report real reachability per seed URL."""
    import json
    from playwright.sync_api import sync_playwright

    seeds = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    print("CHECK MODE — opens each seed URL, scrapes nothing.")
    print("Mode: " + ("YOUR Chrome (--cdp)" if cdp_url else "fresh window") + "\n")
    with sync_playwright() as p:
        sess = Session(p, cdp_url)
        try:
            for s in seeds:
                try:
                    page = sess.context_for(s["platform"]).new_page()
                    page.goto(s["url"], timeout=30000)
                    page.wait_for_timeout(3000)
                    print(f"[{s['platform']:10s}] {s['company']}: "
                          f"{diagnose(page, s['platform'])} — {s['url']}")
                    page.close()
                    time.sleep(1.5)
                except KeyboardInterrupt:
                    print("\nStopped by user (Ctrl+C). Partial results above still stand.")
                    break
                except Exception as e:  # noqa: BLE001 — report per-site, keep going
                    print(f"[{s['platform']:10s}] {s['company']}: ERROR {e}")
        finally:
            sess.close()
    print("\nLOGIN WALL = log in (in your Chrome for --cdp) then re-run --check.")
    print("BLOCKED (bot check) = automation detected; use manual collection for that site.")
    return 0


def scrape_site(site: str, max_pages: int, cdp_url: str | None) -> list[dict]:
    """Per-site collectors. Each returns rows already in contract shape (may be [])."""
    from playwright.sync_api import sync_playwright
    import json

    seeds = [s for s in json.loads(SEED_FILE.read_text(encoding="utf-8"))
             if site == "all" or s["platform"] == site]
    rows: list[dict] = []
    with sync_playwright() as p:
        sess = Session(p, cdp_url)
        try:
            for s in seeds:
                page = sess.context_for(s["platform"]).new_page()
                try:
                    rows.extend(_scrape_seed(page, s, max_pages))
                except Exception as e:  # noqa: BLE001 — one bad seed must not kill run
                    print(f"  SKIP {s['company']} ({s['platform']}): {e}", file=sys.stderr)
                finally:
                    page.close()
                time.sleep(3)  # rate limit: be a polite guest on each site
        finally:
            sess.close()
    return rows


def _scrape_seed(page, seed: dict, max_pages: int) -> list[dict]:
    sel = SELECTORS.get(seed["platform"], SELECTORS["indeed"])
    card, t_sel, loc_sel, date_sel, rate_sel, txt_sel = sel
    out: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()
    for pg in range(max_pages):
        page.goto(seed["url"] + ("&start=%d" % (pg * 10) if pg else ""), timeout=30000)
        page.wait_for_timeout(2500)
        cards = page.query_selector_all(card)
        if not cards:
            print(f"  {seed['company']}: no cards on page {pg + 1} "
                  f"({diagnose(page, seed['platform'])}) — stopping.")
            break
        for c in cards:
            def txt(q: str) -> str:
                el = c.query_selector(q) if q else None
                return (el.inner_text().strip() if el else "")
            title, loc, date, rate, body = (txt(t_sel), txt(loc_sel), txt(date_sel),
                                            txt(rate_sel), txt(txt_sel))
            if not body and not title:
                continue
            if title and not is_cs_it(title):
                continue  # CS/IT only
            if loc and not is_ph(loc):
                continue  # PH only
            if not re.search(r"2026", date):
                continue  # contract: review_date within 2026
            out.append({
                "review_id": make_id(seed["company"], title, date, body, seed["url"]),
                "company_name": seed["company"], "job_title": title or "Unknown",
                "department": "", "seniority_level": "", "employment_status": "Unknown",
                "review_date": date, "rating": norm_rating(rate),
                "review_text": body, "pros": "", "cons": "",
                "location": loc or "Philippines",
                "source_platform": seed["platform"], "source_url": seed["url"],
                "scraped_at": now,
            })
        print(f"  {seed['company']}: page {pg + 1} -> {len(out)} rows so far")
    return out


def append_csv(rows: list[dict]) -> tuple[int, int]:
    """Append rows, skipping duplicate review_id. Returns (added, skipped)."""
    DATA_CSV.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if DATA_CSV.exists():
        with open(DATA_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                seen.add(r.get("review_id", ""))
    else:
        with open(DATA_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()
    added = skipped = 0
    with open(DATA_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        for r in rows:
            if not r.get("review_text") and not r.get("pros") and not r.get("cons"):
                skipped += 1  # contract rule 4: needs meaningful text
                continue
            if r["review_id"] in seen:
                skipped += 1
                continue
            w.writerow({k: r.get(k, "") for k in COLUMNS})
            seen.add(r["review_id"])
            added += 1
    return added, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="reachability check only")
    ap.add_argument("--site", default="all",
                    choices=["all", "indeed", "glassdoor", "jobstreet", "linkedin"])
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--cdp", action="store_true",
                    help="attach to YOUR running Chrome (start it with "
                         "--remote-debugging-port=9222) so your logins apply")
    ap.add_argument("--cdp-url", default=CDP_DEFAULT_URL)
    args = ap.parse_args()
    cdp = args.cdp_url if args.cdp else None
    if args.check:
        return check_mode(cdp)
    rows = scrape_site(args.site, args.max_pages, cdp)
    added, skipped = append_csv(rows)
    print(f"DONE site={args.site}: collected={len(rows)} added={added} skipped={skipped} -> {DATA_CSV}")
    print("Next: python scripts/job_reviews/to_markdown.py && python scripts/job_reviews/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
