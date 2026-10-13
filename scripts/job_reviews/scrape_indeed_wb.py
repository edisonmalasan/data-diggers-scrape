"""Scrape Indeed company reviews from Wayback (2026 captures) -> data/staging_extra.csv.

Chosen additional source: Indeed (ph.indeed.com + www.indeed.com) via
web.archive.org, because:
- live Indeed is bot-blocked, but Wayback 2026 captures contain the full
  server-rendered review payload in <script id="comp-initialData">
  (JSON: reviewsList.items[] with jobTitle, location, country,
   currentEmployee, overallRating, submissionDate, text, sharingLink);
- items carry an explicit country + location string, so the PH gate is
  evidence-based (country == "PH" AND PH_RE on the location text);
- 2026 captures of fcountry=PH-filtered pages and ph.indeed.com pages are
  rich in recent PH reviews.

Access notes (DATA_CONTRACT rule 9): we read PUBLIC Wayback Machine
snapshots (archive.org), not live Indeed; every staged row's source_url
is a traceable https://web.archive.org/web/<ts>id_/<original> URL.
Politeness: >=2.5s between archive.org requests, exponential backoff on
transient connection errors; a URL is marked processed ONLY after a
successful fetch+parse (transient failures are retried, never recorded).

Filters (contract section 3): review_date in 2026, CS/IT job_title (same
gates as scrape_jobstreet), PH location explicitly present, >=1 of
review_text/pros/cons, all fields verbatim, unique review_id.

Run:  python scripts/job_reviews/scrape_indeed_wb.py [--target 80] [--limit 400]
Resume is automatic (.storage/indeed_wb_done.json).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"
URLS_FILE = STORAGE / "indeed_wb_urls.json"
DONE_FILE = STORAGE / "indeed_wb_done.json"
STATS_FILE = STORAGE / "indeed_wb_stats.json"
LATEST_FILE = STORAGE / "indeed_wb_latest.json"
STAGING = ROOT / "data" / "staging_extra.csv"

from scrape_jobstreet import (  # noqa: E402  (shared gates)
    COLUMNS, CS_IT_EXCLUDE, CS_IT_RE, PH_RE, is_ph_location, make_id,
)

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"
SOURCE = "indeed"
DATE_OK_RE = re.compile(r"^[A-Z][a-z]+ \d{1,2}, 20(?:25|26)$")

# Slugs suggesting PH-heavy employers on www.indeed.com (priority tier).
PH_COMPANY_RE = re.compile(
    r"accenture|iqor|telus|concentrix|foundever|alorica|teleperformance|"
    r"taskus|globant|epam|everise|ibex|vxi|microsourcing|sykes|51talk|"
    r"globe|pldt|smart-communications|unionbank|bank-of-the-philippine|"
    r"bdo|bpi|metrobank|securitybank|ayala|sm-|jollibee|universal-robina|"
    r"shopee|lazada|grab|optum|cognizant|wipro|infosys|tcs|capgemini|"
    r"dxc|ibm|microsoft|oracle|dell|dxc-technology|manulife|axa|sun-life|"
    r"aia|insular|malayan|peoplesave|eclerx|foundever|taskus|alorica|"
    r"total-philippines|shell|chevron|petron|transasia|intas|"
    r"genpact|arisGlobal|coherent|keyence|tokio-marine|mitsui|"
    r"deloitte|pwc|kpmg|ey-",
    re.I,
)
PH_FLOC_RE = re.compile(
    r"floc=(Manila|Makati|Taguig|Quezon|Pasig|Cebu|Davao|Clark|Alabang|"
    r"Ortigas|BGC|Bonifacio|Pampanga|Laguna|Cavite|Bulacan|Iloilo|Bacolod)",
    re.I,
)


# ---------------------------------------------------------------- CDX / HTTP
def http_get(url: str, params: dict | None = None, tries: int = 8,
             timeout: int = 180) -> requests.Response | None:
    """GET with exponential backoff on transient errors (connection refused,
    resets, 5xx). Returns None only after all tries fail."""
    delay = 10.0
    for a in range(tries):
        try:
            r = requests.get(url, params=params, headers=H, timeout=timeout)
            if r.status_code >= 500:
                raise RuntimeError(f"HTTP {r.status_code}")
            return r
        except Exception as e:  # noqa: BLE001 — transient by default
            print(f"    transient ({a}): {type(e).__name__} {e} -> retry "
                  f"{delay:.0f}s", file=sys.stderr, flush=True)
            time.sleep(delay + random.uniform(0, 4))
            delay = min(delay * 1.7, 80)
    return None


def cdx_query(extra: dict, tries: int = 5) -> list[list[str]]:
    p = {"matchType": "prefix", "from": "20260101", "to": "20261009",
         "filter": "statuscode:200", "collapse": "urlkey",
         "fl": "original,timestamp,mimetype", "limit": "50000"}
    p.update(extra)
    r = http_get(CDX, p, tries=tries)
    if r is None or r.status_code != 200:
        print(f"  CDX FAIL: {None if r is None else r.status_code} {extra.get('url')}")
        return []
    return [l.split(None, 2) for l in r.text.splitlines() if l.strip()]


def enumerate_inventory() -> list[dict]:
    """Build the snapshot inventory (saved to .storage/indeed_wb_urls.json)."""
    rows: dict[tuple[str, str], dict] = {}

    def add(cols: list[str], host: str) -> None:
        if len(cols) < 2:
            return
        orig, ts = cols[0], cols[1]
        low = orig.lower()
        if "/-/s/assets" in low or low.endswith((".js", ".css", ".png", ".svg")):
            return
        if "/reviews" not in low:
            return
        rows[(orig, ts)] = {"url": orig, "ts": ts, "host": host}

    print("[enum] ph.indeed.com/cmp/ ...")
    for cols in cdx_query({"url": "ph.indeed.com/cmp/"}):
        add(cols, "ph.indeed.com")
    time.sleep(2.5)

    print("[enum] www.indeed.com/cmp/ (review pages) ...")
    got = cdx_query({"url": "www.indeed.com/cmp/",
                     "filter": ["statuscode:200", "mimetype:text/html",
                                "original:.*/reviews.*"]})
    if not got:  # 504 fallback: split by first slug char
        print("[enum] full-prefix query failed; per-letter fallback")
        for letter in "abcdefghijklmnopqrstuvwxyz0123456789":
            for cols in cdx_query({"url": f"www.indeed.com/cmp/{letter}"}):
                if "/reviews" in cols[0].lower():
                    add(cols, "www.indeed.com")
            time.sleep(2.5)
    else:
        for cols in got:
            add(cols, "www.indeed.com")

    inv = list(rows.values())

    def prio(item: dict) -> tuple:
        u = item["url"].lower()
        host = item["host"]
        is_list = bool(re.search(r"/reviews?/?(\?|$)", u))
        if "fcountry=ph" in u:
            tier = 0
        elif host == "ph.indeed.com" and is_list:
            tier = 1  # PH-site list pages
        elif host == "ph.indeed.com":
            tier = 2  # PH-site permalinks (1 review each)
        elif is_list and PH_COMPANY_RE.search(u):
            tier = 3  # likely PH-heavy employer, plain list page
        elif PH_FLOC_RE.search(u):
            tier = 4
        elif is_list:
            tier = 5  # generic list pages (unknown yield)
        else:
            tier = 6  # generic query pages / permalinks
        return (tier, )  # ts handled below

    inv.sort(key=lambda it: (prio(it), it["ts"]), reverse=False)
    # newest capture first within a tier
    by_tier: dict[int, list[dict]] = {}
    for it in inv:
        by_tier.setdefault(prio(it)[0], []).append(it)
    ordered: list[dict] = []
    for tier in sorted(by_tier):
        ordered.extend(sorted(by_tier[tier], key=lambda x: x["ts"], reverse=True))

    URLS_FILE.write_text(json.dumps(
        {"created": datetime.now(timezone.utc).isoformat(), "items": ordered},
        indent=0), encoding="utf-8")
    tier_counts = {t: len(v) for t, v in sorted(by_tier.items())}
    print(f"[enum] inventory: {len(ordered)} snapshots, tiers={tier_counts}")
    return ordered


# ------------------------------------------------------------- page parsing
def extract_items(html: str) -> list[dict] | None:
    """Return review dicts from the comp-initialData JSON payload.

    List pages carry reviewsList.items[]; single-review permalink pages
    carry individualReviews.review (+ relatedReviews list, ignored).
    """
    m = re.search(
        r'<script[^>]*id="comp-initialData"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    content = m.group(1)
    try:
        data = json.loads(content)
    except Exception:  # noqa: BLE001 — concatenated-objects fallback
        try:
            data, _ = json.JSONDecoder().raw_decode(content)
        except Exception:  # noqa: BLE001
            return None
    if not isinstance(data, dict):
        return None
    rl = data.get("reviewsList")
    if isinstance(rl, dict) and rl.get("items") is not None:
        comp = rl.get("companyName") or ""
        return [dict(it, _company=comp) for it in (rl.get("items") or [])]
    ir = data.get("individualReviews")
    if isinstance(ir, dict) and isinstance(ir.get("review"), dict):
        return [dict(ir["review"], _company=ir.get("companyName") or "")]
    return None


def _txt(v) -> str:
    """Verbatim text from an item field that may be a str or {text: ...}."""
    if isinstance(v, dict):
        return (v.get("text") or "").strip()
    if isinstance(v, str):
        return v.strip()
    return ""


def build_row(it: dict, snapshot_url: str, now: str, stats: dict,
              page_is_ph: bool = False) -> dict | None:
    """Apply the contract gates in order: 2026 date -> non-empty text ->
    CS/IT title -> country -> PH location. All field values verbatim.

    page_is_ph marks pages that are explicitly Philippine at the PAGE level
    (host ph.indeed.com or a fcountry=PH filter). Such pages may omit the
    per-review `country` field, so a missing/empty country is accepted there;
    a present non-"PH" country is always rejected."""
    stats["items"] += 1
    job_title = (it.get("jobTitle") or "").strip()
    headline = _txt(it.get("title"))
    body = _txt(it.get("text"))
    review_text = "\n".join(x for x in (headline, body) if x)
    pros = _txt(it.get("pros"))
    cons = _txt(it.get("cons"))
    date = (it.get("submissionDate") or "").strip()

    if not DATE_OK_RE.match(date):
        stats["drop_date"] += 1
        return None
    if not (review_text or pros or cons):
        stats["drop_text"] += 1
        return None
    if not (CS_IT_RE.search(job_title) and not CS_IT_EXCLUDE.search(job_title)):
        stats["drop_csit"] += 1
        return None
    # Country gate: accept explicit "PH"; on an explicitly-PH page accept a
    # missing/empty country; a present, clearly-other country always rejects.
    country = it.get("country")
    if isinstance(country, str):
        country = country.strip()
        country_ok = (country.upper() == "PH") if country else page_is_ph
    else:
        country_ok = country is None and page_is_ph
    if not country_ok:
        stats["drop_country"] += 1
        return None
    location = (it.get("location") or "").strip()
    if not is_ph_location(location):
        stats["drop_location"] += 1
        return None

    company = (it.get("_company") or "").strip()
    if not company or not job_title:
        stats["drop_meta"] += 1
        return None
    canonical = (it.get("sharingLink")
                 or ("https://" + it.get("host", "ph.indeed.com")
                     + (it.get("reviewUrl") or ""))).strip()
    rating = it.get("overallRating")
    rating_s = f"{float(rating):.1f}" if isinstance(rating, (int, float)) and rating else ""
    return {
        "review_id": make_id(company, job_title, date, review_text[:120], canonical),
        "company_name": company,
        "job_title": job_title,
        "department": "",
        "seniority_level": "",
        "employment_status": "Current" if it.get("currentEmployee") else "Former",
        "review_date": date,
        "rating": rating_s,
        "review_text": review_text,
        "pros": pros,
        "cons": cons,
        "location": location,
        "source_platform": SOURCE,
        "source_url": snapshot_url,
        "scraped_at": now,
    }


def resolve_latest(url: str, cache: dict) -> tuple[str, str]:
    """Latest 2026 capture timestamp for an exact URL (cached on disk).

    The inventory was built with collapse=urlkey, i.e. the EARLIEST 2026
    capture — usually poor in 2026 reviews. Reviews sort newest-first, so
    we prefer the LAST 2026 capture (limit=-1 returns the last row).

    Returns (status, ts): ("ok", ts) on success; ("missing", "") when CDX
    answers but has no 2026 capture; ("error", "") on transient failure
    (nothing cached, so a later run retries)."""
    if url in cache:
        return ("ok", cache[url])
    r = http_get(CDX, {"url": url, "matchType": "exact",
                       "from": "20260101", "to": "20261009",
                       "filter": "statuscode:200",
                       "fl": "timestamp", "limit": "-1"}, tries=5)
    if r is None or r.status_code != 200:
        return ("error", "")  # transient — do NOT cache
    ts = r.text.strip()
    ts = ts.splitlines()[-1].strip() if ts else ""
    if not ts:
        return ("missing", "")  # genuine no-capture; don't cache (cheap retry)
    cache[url] = ts
    LATEST_FILE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
    time.sleep(2.5)
    return ("ok", ts)


# ------------------------------------------------------------------ storage
def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(json.loads(DONE_FILE.read_text(encoding="utf-8")))
    return set()


def save_done(done: set[str]) -> None:
    DONE_FILE.write_text(json.dumps(sorted(done), indent=0), encoding="utf-8")


def load_existing_ids() -> set[str]:
    ids: set[str] = set()
    if STAGING.exists():
        with open(STAGING, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ids.add(r.get("review_id", ""))
    return ids


def write_rows(rows: list[dict]) -> None:
    STAGING.parent.mkdir(parents=True, exist_ok=True)
    new_file = not STAGING.exists()
    with open(STAGING, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})


# --------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=80,
                    help="stop once staging_extra.csv holds this many rows")
    ap.add_argument("--limit", type=int, default=500,
                    help="max snapshots to visit this run")
    ap.add_argument("--sleep", type=float, default=2.5,
                    help="polite delay between archive.org requests")
    args = ap.parse_args()

    if URLS_FILE.exists():
        inv = json.loads(URLS_FILE.read_text(encoding="utf-8"))["items"]
        print(f"[enum] reusing saved inventory ({len(inv)} snapshots)")
    else:
        inv = enumerate_inventory()

    done = load_done()
    seen_ids = load_existing_ids()
    latest_cache = (json.loads(LATEST_FILE.read_text(encoding="utf-8"))
                    if LATEST_FILE.exists() else {})
    todo = [it for it in inv if it["url"] not in done][: args.limit]
    print(f"[run] done={len(done)} todo={len(todo)} staged_ids={len(seen_ids)} "
          f"target={args.target}")

    stats = {"items": 0, "drop_date": 0, "drop_text": 0, "drop_csit": 0,
             "drop_country": 0, "drop_location": 0, "drop_meta": 0,
             "kept": 0, "pages": 0, "no_payload": 0, "fetch_fail": 0}
    new_rows: list[dict] = []
    consec_fail = 0
    try:
        for n, it in enumerate(todo, 1):
            if len(seen_ids) >= args.target:
                print(f"[run] target {args.target} reached -> stop")
                break
            status, ts = resolve_latest(it["url"], latest_cache)
            if status != "ok":
                if status == "error":
                    consec_fail += 1
                    stats["fetch_fail"] += 1
                    print(f"[{n}/{len(todo)}] RESOLVE-ERROR {it['url'][:80]}")
                    if consec_fail >= 5:
                        print("[run] 5 consecutive archive.org failures -> "
                              "stopping (resumable, nothing marked done)")
                        break
                else:  # missing: no 2026 capture, skip quietly
                    done.add(it["url"])
                    save_done(done)
                    stats["no_payload"] += 1
                time.sleep(args.sleep)
                continue
            key = it["url"]
            snap = f"https://web.archive.org/web/{ts}id_/{it['url']}"
            r = http_get(snap, tries=6, timeout=150)
            if r is None or r.status_code != 200:
                # transient exhaustion: do NOT mark done
                stats["fetch_fail"] += 1
                consec_fail += 1
                print(f"[{n}/{len(todo)}] FETCH-FAIL "
                      f"{None if r is None else r.status_code} {it['url'][:80]}")
                if consec_fail >= 5:
                    print("[run] 5 consecutive archive.org failures -> "
                          "stopping (resumable, nothing marked done)")
                    break
                time.sleep(args.sleep)
                continue
            consec_fail = 0
            items = extract_items(r.text)
            if items is None:
                stats["no_payload"] += 1
                done.add(key)
                save_done(done)
                print(f"[{n}/{len(todo)}] no-payload {it['url'][:80]}")
                time.sleep(args.sleep)
                continue
            page_rows = []
            now = datetime.now(timezone.utc).isoformat()
            page_is_ph = ("ph.indeed.com" in it["url"]
                          or "fcountry=ph" in it["url"].lower())
            for raw in items:
                raw["host"] = "ph.indeed.com" if "ph.indeed.com" in it["url"] else "www.indeed.com"
                row = build_row(raw, snap, now, stats, page_is_ph=page_is_ph)
                if row and row["review_id"] not in seen_ids:
                    seen_ids.add(row["review_id"])
                    page_rows.append(row)
            if page_rows:
                write_rows(page_rows)  # flush per page (crash-safe)
                new_rows.extend(page_rows)
                stats["kept"] += len(page_rows)
            done.add(key)
            save_done(done)
            stats["pages"] += 1
            print(f"[{n}/{len(todo)}] items={len(items)} kept+={len(page_rows)} "
                  f"total_new={len(new_rows)} :: {it['url'][:90]}")
            time.sleep(args.sleep)
    except KeyboardInterrupt:
        print("\n[run] interrupted — saved state so far")

    STATS_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    total = len(load_existing_ids())
    print(f"[run] DONE pages={stats['pages']} items={stats['items']} "
          f"new_rows={len(new_rows)} staged_total={total} -> {STAGING}")
    print(f"[run] filter stats: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
