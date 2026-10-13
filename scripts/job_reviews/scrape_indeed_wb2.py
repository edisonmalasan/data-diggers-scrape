"""Second-pass Indeed/Wayback sweep with the fixed country gate.

Recovers rows the previous run dropped at the country gate
(.storage/EXTRA_SOURCE_REPORT.md: drop_country=42, kept=0).  The fix lives in
scrape_indeed_wb.build_row(): a review now passes the country gate when
country == "PH" OR when the country field is missing/empty AND the PAGE is
explicitly Philippine (host ph.indeed.com or a fcountry=PH filter).  A
present, clearly-other country (e.g. "US") still rejects.  Every other gate
and its order is unchanged: 2026 date -> non-empty text (>=1 of
review_text/pros/cons) -> CS_IT_RE and not CS_IT_EXCLUDE on job_title ->
country -> is_ph_location(location).  All field values are verbatim from the
Wayback payload; nothing is fabricated.

Rows -> data/staging_indeed.csv (COLUMNS from scrape_jobstreet, header on
creation, append + flush per page, deduped by review_id in-session).
data/job_reviews_raw.csv is NOT touched (central merge script owns it).

Fetch rules (requests only, no browser, no live sites):
- snapshots:  https://web.archive.org/web/<ts>id_/<original_url>  (fetch)
  source_url:  https://web.archive.org/web/<ts>/<original_url>     (canonical)
- 1.5-3s polite sleep between archive.org requests;
- 429 / connection failures / 5xx -> exponential backoff 5*2^attempt,
  capped 60s;
- transient failures are never marked done (retryable);
- circuit breaker: stop after 8 consecutive archive.org failures.

State (resumable): .storage/indeed_wb_queue3.json (priority queue, built
offline from the inventory), .storage/indeed_wb_done3.json,
.indeed_wb_stats3.json (accumulating funnel + kept URLs), shared
.indeed_wb_latest.json (latest-capture cache).

Run:
  python scripts/job_reviews/scrape_indeed_wb2.py --queue-only   # offline plan
  python scripts/job_reviews/scrape_indeed_wb2.py                 # sweep
  python scripts/job_reviews/scrape_indeed_wb2.py --report-only  # re-report
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
from urllib.parse import parse_qsl, urlsplit

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import CDX, PH_FLOC_RE, build_row, extract_items  # noqa: E402
from scrape_jobstreet import COLUMNS, CS_IT_EXCLUDE, CS_IT_RE, make_id  # noqa: E402

URLS_FILE = STORAGE / "indeed_wb_urls.json"
OLD_DONE_FILE = STORAGE / "indeed_wb_done.json"      # previous (buggy) run
QUEUE_FILE = STORAGE / "indeed_wb_queue3.json"
DONE_FILE = STORAGE / "indeed_wb_done3.json"
STATS_FILE = STORAGE / "indeed_wb_stats3.json"
LATEST_FILE = STORAGE / "indeed_wb_latest.json"
RUNLOG_FILE = STORAGE / "indeed_wb_run3.log"
REPORT_FILE = STORAGE / "INDEED_RESWEEP_REPORT.md"
STAGING = ROOT / "data" / "staging_indeed.csv"

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
SOURCE = "Indeed"
LATE_TS = "20260901"            # Sep/Oct 2026 captures preferred
CDX_FROM = "20260101"           # capture window used by resolve_latest()
CDX_TO = "20261009"
CIRCUIT_MAX = 8                 # consecutive archive.org failures -> stop
DEFAULT_CAP = 2500              # total snapshot fetches this sweep
DEFAULT_MAX_SECONDS = 12600     # 3.5 h hard runtime bound

# Brief tier (d): PH-heavy employers, word-boundary match on the cmp slug
# (slug hyphens act as word boundaries, so "Grey"/"Money" do not match "ey").
PH_HEAVY_RE = re.compile(
    r"\b(accenture|teleperformance|concentrix|ibm|cognizant|tcs|capgemini|"
    r"telus|taskus|alorica|deloitte|ey|kpmg|pwc|sap|globe|pldt|jollibee|"
    r"shopee|lazada|grab)\b",
    re.I,
)

STAT_KEYS = [
    "items", "drop_date", "drop_text", "drop_csit", "drop_country",
    "drop_location", "drop_meta", "kept", "dup_skipped",
    "fetched", "pages", "no_payload", "no_capture", "fetch_bad",
    "fetch_fail", "resolve_fail",
]


# ------------------------------------------------------------------ helpers
def log(msg: str) -> None:
    print(msg, flush=True)
    with open(RUNLOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def polite() -> None:
    time.sleep(random.uniform(1.5, 3.0))


def archive_get(url: str, params: dict | None = None, tries: int = 4,
                timeout: int = 150) -> requests.Response | None:
    """GET with exponential backoff: 5*2^attempt capped at 60s on 429,
    connection errors and 5xx.  Returns a Response for any other status
    (permanent answers such as 404), None only after transient retries are
    exhausted (caller must NOT mark the page done in that case)."""
    delay = 5.0
    last = ""
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=H, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                last = f"HTTP {r.status_code}"
            else:
                return r
        except requests.RequestException as e:
            last = f"{type(e).__name__}: {e}"
        if attempt + 1 < tries:
            wait = min(delay, 60.0)
            log(f"    transient ({attempt + 1}) {last} -> backoff {wait:.0f}s")
            time.sleep(wait + random.uniform(0, 2))
        delay *= 2
    log(f"    gave up after {tries} tries: {last}")
    return None


def resolve_latest(url: str, cache: dict) -> tuple[str, str]:
    """Latest capture timestamp for an exact URL in the active window
    (cached on disk). Returns ("ok", ts) | ("missing", "") | ("error", "")."""
    if url in cache:
        return ("ok", cache[url])
    r = archive_get(CDX, {"url": url, "matchType": "exact",
                          "from": CDX_FROM, "to": CDX_TO,
                          "filter": "statuscode:200",
                          "fl": "timestamp", "limit": "-1"}, tries=3)
    if r is None or r.status_code != 200:
        return ("error", "")   # transient — not cached, retried next run
    ts = r.text.strip()
    ts = ts.splitlines()[-1].strip() if ts else ""
    if not ts:
        return ("missing", "")  # genuinely no 2026 capture
    cache[url] = ts
    LATEST_FILE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
    polite()
    return ("ok", ts)


# ------------------------------------------------------------- queue build
def _norm_params(url: str) -> frozenset:
    return frozenset((k.lower(), v.lower())
                     for k, v in parse_qsl(urlsplit(url).query))


def _is_list_page(url: str) -> bool:
    return bool(re.search(r"/reviews?/?$", urlsplit(url).path))


def csit_fjobtitle(url: str) -> bool:
    """True when the page's fjobtitle filter is itself a CS/IT title."""
    for k, v in parse_qsl(urlsplit(url).query):
        if k.lower() == "fjobtitle":
            if CS_IT_RE.search(v) and not CS_IT_EXCLUDE.search(v):
                return True
    return False


def page_tier(page: dict, revisit: set[str]) -> int:
    """Priority tiers (first match wins):
    -1 previously fetched PH-relevant pages (proven to hold 2026 CS/IT
       items — first priority now that the country gate is fixed),
     0 ph.indeed.com pages                     (brief a)
     1 fcountry=PH pages                       (brief b)
     2 CS/IT fjobtitle-filtered pages           (brief c)
     3 PH-heavy employer slugs                  (brief d)
     4 PH-city floc-filtered pages
     5 other list pages / 6 permalinks          (brief e)

    The revisit boost (-1) only applies to PH-relevant pages (base tier
    <= 4); generic pages previously fetched keep their natural tier."""
    url = page["url"]
    base = _base_tier(page)
    if url in revisit and base <= 4:
        return -1
    return base


def _base_tier(page: dict) -> int:
    url = page["url"]
    low = url.lower()
    path = urlsplit(url).path
    if page["host"] == "ph.indeed.com":
        return 0
    if "fcountry=ph" in low:
        return 1
    if csit_fjobtitle(url):
        return 2
    if PH_HEAVY_RE.search(path):
        return 3
    if PH_FLOC_RE.search(low):
        return 4
    if _is_list_page(url):
        return 5
    return 6


def build_queue(cap: int) -> dict:
    """Offline: dedupe inventory (same host+path+same filter-params set =
    one page, keep the latest ts), order by tier with list pages and
    late-2026 (Sep/Oct) captures first, cap at `cap` fetches."""
    inv = json.loads(URLS_FILE.read_text(encoding="utf-8"))["items"]
    revisit: set[str] = set()
    if OLD_DONE_FILE.exists():
        revisit = set(json.loads(OLD_DONE_FILE.read_text(encoding="utf-8")))

    pages: dict[tuple, dict] = {}
    for it in inv:
        sp = urlsplit(it["url"])
        key = (it["host"], sp.path, _norm_params(it["url"]))
        cur = pages.get(key)
        if cur is None or it["ts"] > cur["ts"]:     # keep the LATEST ts
            pages[key] = {"host": it["host"], "url": it["url"], "ts": it["ts"]}

    buckets: dict[int, list[dict]] = {}
    for p in pages.values():
        p["tier"] = page_tier(p, revisit)
        buckets.setdefault(p["tier"], []).append(p)

    ordered: list[dict] = []
    tier_counts: dict[str, int] = {}
    for t in sorted(buckets):
        b = buckets[t]
        b.sort(key=lambda p: p["ts"], reverse=True)          # newest capture
        b.sort(key=lambda p: 0 if p["ts"] >= LATE_TS else 1)  # late-2026 first
        b.sort(key=lambda p: 0 if _is_list_page(p["url"]) else 1)
        ordered.extend(b)
        tier_counts[str(t)] = len(b)

    queue = ordered[:cap]
    out = {
        "created": datetime.now(timezone.utc).isoformat(),
        "inventory_items": len(inv),
        "unique_pages": len(pages),
        "cap": cap,
        "tier_counts": tier_counts,
        "queued": len(queue),
        "items": queue,
    }
    QUEUE_FILE.write_text(json.dumps(out, indent=0), encoding="utf-8")
    return out


def load_queue(cap: int) -> dict:
    if QUEUE_FILE.exists():
        q = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        if q.get("cap") == cap:
            return q
    return build_queue(cap)


# ----------------------------------------------------------------- storage
def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(json.loads(DONE_FILE.read_text(encoding="utf-8")))
    return set()


def save_done(done: set[str]) -> None:
    DONE_FILE.write_text(json.dumps(sorted(done), indent=0), encoding="utf-8")


def load_stats() -> dict:
    if STATS_FILE.exists():
        s = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        s.setdefault("kept_urls", [])
        return s
    s = {k: 0 for k in STAT_KEYS}
    s["kept_urls"] = []
    return s


def save_stats(stats: dict) -> None:
    STATS_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")


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
        f.flush()


# ------------------------------------------------------------------ report
def write_report(stats: dict) -> None:
    examples: list[dict] = []
    total_indeed = 0
    if STAGING.exists():
        with open(STAGING, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("source_platform") == SOURCE:
                    total_indeed += 1
                    if len(examples) < 12:
                        examples.append(r)

    lines = [
        "# Indeed via Wayback — re-sweep (country-gate fix)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Fix: `build_row()` in scrape_indeed_wb.py now accepts `country == \"PH\"`",
        "OR a missing/empty country on an explicitly-PH page (host ph.indeed.com",
        "or `fcountry=PH`).  A present non-PH country still rejects.  All other",
        "gates unchanged and in order: 2026 date -> non-empty text -> CS/IT title",
        "-> country -> is_ph_location(location).  Fields verbatim, no fabrication.",
        "",
        "Staging file: `data/staging_indeed.csv` (data/job_reviews_raw.csv untouched).",
        "",
        "## Funnel (this sweep)",
        "",
        "| metric | count |",
        "| --- | --- |",
        f"| snapshot fetches OK (fetched) | {stats['fetched']} |",
        f"| pages parsed (pages) | {stats['pages']} |",
        f"| pages without payload (no_payload) | {stats['no_payload']} |",
        f"| pages with no 2026 capture (no_capture) | {stats['no_capture']} |",
        f"| permanent fetch answers (fetch_bad) | {stats['fetch_bad']} |",
        f"| transient fetch failures (retryable) | {stats['fetch_fail']} |",
        f"| transient CDX failures (retryable) | {stats['resolve_fail']} |",
        f"| review items parsed | {stats['items']} |",
        f"| drop_date | {stats['drop_date']} |",
        f"| drop_text | {stats['drop_text']} |",
        f"| drop_csit | {stats['drop_csit']} |",
        f"| drop_country | {stats['drop_country']} |",
        f"| drop_location | {stats['drop_location']} |",
        f"| drop_meta | {stats['drop_meta']} |",
        f"| duplicate review_id skipped | {stats['dup_skipped']} |",
        f"| **kept rows** | **{stats['kept']}** |",
        f"| Indeed rows in staging_indeed.csv | {total_indeed} |",
        "",
        "Previous run (before the fix): pages=254 items=1471 drop_date=986",
        "drop_csit=443 drop_country=42 kept=0.",
        "",
        "## Example kept rows",
        "",
    ]
    if examples:
        lines += ["| company | job_title | review_date | location |",
                  "| --- | --- | --- | --- |"]
        for r in examples:
            lines.append(f"| {r['company_name']} | {r['job_title']} | "
                         f"{r['review_date']} | {r['location']} |")
    else:
        lines.append("(no kept rows yet)")
    lines += ["", "## URLs that produced kept rows", ""]
    if stats["kept_urls"]:
        lines += [f"- {u}" for u in stats["kept_urls"]]
    else:
        lines.append("(none)")
    lines += [
        "",
        "## Why kept = 0 (evidence that the source is exhausted, not the gate)",
        "",
        "The country gate fix was verified by `test_country_gate.py` (16/16).",
        "Diagnostics then tested EVERY inventory class for PH-country rows:",
        "",
        "1. **ph.indeed.com (complete universe)** — CDX domain probe returns 72",
        "   review-ish URLs, all in the inventory, all fetched (71 in run 3 + 1",
        "   revisit). Funnel: date 113, text 0, csit 4 (empty/non-CS titles),",
        "   country 0, location 0, kept 0. Each ph URL has exactly ONE 2026",
        "   capture (no later Sep/Oct snapshots exist). Corpus skews pre-2026.",
        "2. **ph overview pages** (`/cmp/<slug>`, 23 distinct companies, not in",
        "   the review inventory) — probed: 0 embedded review items",
        "   (`.storage/diag_ph_overview.log`).",
        "3. **www PH-relevant queued pages** (tiers 2/3/4: CS/IT fjobtitle,",
        "   PH-heavy slugs, PH-floc) — 84 pages fetched: 114 items, all",
        "   `country='US'`, passers=0 (`.storage/diag_www_passers.log`).",
        "4. **www done list pages** (source of drop_country=111) — 60-page random",
        "   refetch: 207 items = US 206 / IN 1, date+csit passers = 7, all US,",
        "   PH passers = 0 (`.storage/diag_done_passers.log`).",
        "5. **www ?fcountry=ALL pages** (332 in inventory, the only www class",
        "   showing non-US reviews) — 30-page sample: US 13 / AU 1 / SK 1 / IE 1,",
        "   passers = 0.",
        "6. **www detail permalinks** (28,424 in inventory) — 50-page sample",
        "   (30 PH-heavy slugs): all `country='US'`, passers = 0.",
        "7. **CDX negative probes** — www `fcountry=PH`: 0 URLs; www `floc=` PH",
        "   cities: 0 URLs; `indeed.ph` / `www.indeed.ph`: 0 captures.",
        "",
        "Conclusion: `country='PH'` exists only on ph.indeed.com, whose 2026",
        "captures die at the date gate (96%) and CS/IT gate (rest). www pages",
        "carry US/IN/AU/SK/IE reviews that correctly fail the country gate.",
        "kept=0 is the contract-correct outcome; no fabrication was applied.",
        "",
        "## State files (resumable)",
        "",
        "- `scripts/job_reviews/.storage/indeed_wb_queue3.json` — priority queue",
        "- `scripts/job_reviews/.storage/indeed_wb_done3.json` — pages processed",
        "- `scripts/job_reviews/.storage/indeed_wb_stats3.json` — funnel + kept URLs",
        "- `scripts/job_reviews/.storage/indeed_wb_latest.json` — latest-capture cache",
        "- `scripts/job_reviews/.storage/indeed_wb_run3.log` — run log",
        "",
    ]
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    log(f"[report] {REPORT_FILE}")


# --------------------------------------------------------------------- run
def run(args: argparse.Namespace) -> int:
    q = load_queue(args.cap)
    log(f"[queue] unique_pages={q['unique_pages']} tiers={q['tier_counts']} "
        f"queued={q['queued']} (cap={q['cap']})")

    done = load_done()
    seen_ids = load_existing_ids()
    stats = load_stats()
    latest = json.loads(LATEST_FILE.read_text(encoding="utf-8")) \
        if LATEST_FILE.exists() else {}
    todo = [e for e in q["items"] if e["url"] not in done]
    log(f"[run] done={len(done)} todo={len(todo)} staged_ids={len(seen_ids)} "
        f"kept_so_far={stats['kept']}")

    consec = 0
    t0 = time.time()
    stopped = ""
    try:
        for i, entry in enumerate(todo, 1):
            if time.time() - t0 > args.max_seconds:
                stopped = "time budget reached"
                break
            if consec >= CIRCUIT_MAX:
                stopped = f"{CIRCUIT_MAX} consecutive archive.org failures"
                break
            url = entry["url"]

            status, ts = resolve_latest(url, latest)
            if status == "error":
                consec += 1
                stats["resolve_fail"] += 1
                log(f"[{i}/{len(todo)}] RESOLVE-ERROR consec={consec} "
                    f"{url[:90]}")
                polite()
                continue
            if status == "missing":
                stats["no_capture"] += 1
                done.add(url)
                save_done(done)
                polite()
                continue

            snap = f"https://web.archive.org/web/{ts}id_/{url}"
            r = archive_get(snap, timeout=150)
            if r is None:                    # transient — NOT marked done
                consec += 1
                stats["fetch_fail"] += 1
                log(f"[{i}/{len(todo)}] FETCH-FAIL consec={consec} {url[:90]}")
                continue
            if r.status_code != 200:         # permanent answer (404 etc.)
                stats["fetch_bad"] += 1
                done.add(url)
                save_done(done)
                log(f"[{i}/{len(todo)}] HTTP {r.status_code} {url[:90]}")
                polite()
                continue
            consec = 0
            stats["fetched"] += 1

            canonical = f"https://web.archive.org/web/{ts}/{url}"
            items = extract_items(r.text)
            if items is None:
                stats["no_payload"] += 1
                done.add(url)
                save_done(done)
                log(f"[{i}/{len(todo)}] no-payload {url[:90]}")
                polite()
                continue
            stats["pages"] += 1

            page_is_ph = (entry["host"] == "ph.indeed.com"
                          or "fcountry=ph" in url.lower())
            now = datetime.now(timezone.utc).isoformat()
            rows: list[dict] = []
            for raw in items:
                raw["host"] = entry["host"]
                row = build_row(raw, canonical, now, stats,
                                page_is_ph=page_is_ph)
                if row is None:
                    continue
                row["source_platform"] = "Indeed"  # contract value (wb1 uses lowercase)
                if row["review_id"] in seen_ids:
                    stats["dup_skipped"] += 1
                    continue
                seen_ids.add(row["review_id"])
                rows.append(row)
            if rows:
                write_rows(rows)             # append + flush per page
                stats["kept"] += len(rows)
                stats["kept_urls"].append(url)
            done.add(url)
            save_done(done)
            save_stats(stats)
            log(f"[{i}/{len(todo)}] items={len(items)} kept+={len(rows)} "
                f"total_kept={stats['kept']} :: {url[:100]}")
            polite()
    except KeyboardInterrupt:
        stopped = "interrupted"

    if stopped:
        log(f"[run] stopping: {stopped} (state saved, resumable)")
    save_stats(stats)
    write_report(stats)
    log(f"[run] DONE fetched={stats['fetched']} pages={stats['pages']} "
        f"items={stats['items']} kept={stats['kept']} "
        f"staged_ids={len(load_existing_ids())} -> {STAGING}")
    log(f"[run] funnel: {{'drop_date': {stats['drop_date']}, "
        f"'drop_text': {stats['drop_text']}, 'drop_csit': {stats['drop_csit']}, "
        f"'drop_country': {stats['drop_country']}, "
        f"'drop_location': {stats['drop_location']}, "
        f"'drop_meta': {stats['drop_meta']}, 'kept': {stats['kept']}}}")
    return 0


def main() -> int:
    global URLS_FILE, QUEUE_FILE, DONE_FILE, STATS_FILE, RUNLOG_FILE, \
        REPORT_FILE, LATEST_FILE, LATE_TS, CDX_FROM, CDX_TO
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP,
                    help="max snapshot fetches in the priority queue")
    ap.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS,
                    help="hard runtime bound for this run (resumable)")
    ap.add_argument("--queue-only", action="store_true",
                    help="build/print the queue offline and exit")
    ap.add_argument("--report-only", action="store_true",
                    help="regenerate the report from saved stats and exit")
    ap.add_argument("--year", type=int, default=2026, choices=(2025, 2026),
                    help="capture window + state files: 2026 (queue3, default) "
                         "or 2025 captures (queue4) — harvests 2025 reviews")
    args = ap.parse_args()

    if args.year == 2025:
        URLS_FILE = STORAGE / "indeed_wb_urls_2025.json"
        QUEUE_FILE = STORAGE / "indeed_wb_queue4.json"
        DONE_FILE = STORAGE / "indeed_wb_done4.json"
        STATS_FILE = STORAGE / "indeed_wb_stats4.json"
        RUNLOG_FILE = STORAGE / "indeed_wb_run4.log"
        REPORT_FILE = STORAGE / "INDEED_2025_REPORT.md"
        LATEST_FILE = STORAGE / "indeed_wb_latest_2025.json"
        LATE_TS = "20250901"     # late-2025 captures show the most 2025 reviews
        CDX_FROM, CDX_TO = "20250101", "20251231"
        log(f"[mode] 2025 captures: inventory={URLS_FILE.name} "
            f"queue={QUEUE_FILE.name} done={DONE_FILE.name}")

    if args.report_only:
        write_report(load_stats())
        return 0
    if args.queue_only:
        q = build_queue(args.cap)
        print(json.dumps({k: q[k] for k in ("created", "inventory_items",
                                            "unique_pages", "cap",
                                            "tier_counts", "queued")},
                         indent=2))
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
