"""Live Glassdoor scraper (Playwright, anonymous) -> data/staging_glassdoor.csv.

Access model (measured, see probe_live5/6):
  - anonymous users get exactly the 3 NEWEST reviews per URL (_P2 login-walled)
  - ?filter.jobTitleExact=<title> re-slices the pool to that job title
  - default sort is newest-first, so fetched reviews are 2026 for active cos
  - review payload lives in the RSC stream (self.__next_f), object fields:
      reviewId, reviewDateTime, jobTitle.text, location.name(+type),
      summary, pros, cons, employmentStatus, ratingOverall, employer.shortName

Per-review gates (verbatim, no fabrication):
  1. reviewDateTime year == 2026
  2. jobTitle.text passes CS_IT_RE and not CS_IT_EXCLUDE (drops "Anonymous")
  3. location.name passes is_ph_location() (PH city/country)
  4. at least one of summary/pros/cons non-empty

Rows append to a staging CSV; merge_staging.py folds them into
data/job_reviews_raw.csv (append-only, dedupe by review_id, same gates).

Resumable: processed URLs are recorded in .storage/gd_live_done.json.
Cloudflare Turnstile: handled by clicking the widget; on failure we back off
and retry. The persistent profile keeps any cf_clearance cookie.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from scrape_jobstreet import (COLUMNS, CS_IT_EXCLUDE, CS_IT_RE,
                              is_ph_location, make_id)

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"
ROOT = HERE.parents[1]

CHALLENGE = ("Just a moment", "Verifying you are human", "Security Check",
             "Attention Required")
RATELIMIT = ("Glassdoor | Glassdoor", "Pardon Our Interruption",
             "Too Many Requests", "Request Rejected")
LOGIN_TITLES = ("Log In | Glassdoor", "Sign In | Glassdoor")

# Concrete CS/IT titles to slice by (jobTitleExact; gate re-checks actual text).
TITLES = [
    "Software Engineer", "Software Developer", "Senior Software Engineer",
    "Full Stack Developer", "Frontend Developer", "Backend Developer",
    "Web Developer", "Mobile Developer", "Android Developer",
    "DevOps Engineer", "Cloud Engineer", "Data Analyst", "Data Engineer",
    "Data Scientist", "Database Administrator", "Systems Administrator",
    "Network Engineer", "Information Security Analyst",
    "Quality Assurance Engineer", "Test Engineer",
    "Technical Support Engineer", "IT Support", "IT Helpdesk",
    "Help Desk Analyst", "Application Support Analyst", "Programmer",
    "Software Architect", "Business Analyst", "Solutions Engineer",
    "Systems Analyst",
]

BASE = "https://www.glassdoor.com/Reviews/{slug}-Reviews-E{eid}.htm"


def extract_reviews(html: str) -> list[dict] | None:
    """Reviews from the RSC payload. None = payload absent (bad page)."""
    payload = "".join(re.findall(
        r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S))
    payload = payload.replace('\\"', '"').replace("\\\\", "\\")
    i = payload.find('"reviews":[')
    if i < 0:
        return None
    try:
        arr, _ = json.JSONDecoder().raw_decode(payload[payload.index("[", i):])
    except Exception:  # noqa: BLE001
        return None
    return arr if isinstance(arr, list) else None


def click_widget(page) -> bool:
    for f in page.frames:
        if "challenges.cloudflare.com" not in f.url:
            continue
        try:
            box = f.frame_element().bounding_box()
        except Exception:  # noqa: BLE001
            continue
        if box and box.get("width", 0) > 10:
            page.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
            return True
    return False


def canonical_base(final_url: str, cur_base: str) -> str:
    """Canonical reviews-URL base derived from the post-redirect URL.

    Some employer slugs 301-redirect and DROP the query string
    (Teleperformance-Philippines -> TP), silently killing every filter.
    After an 'ok' load we rebuild slices from the final path instead.
    """
    m = re.search(r"(/Reviews/[^/?#]+?-Reviews-E\d+)\.htm", final_url)
    if not m:
        return cur_base
    cand = "https://www.glassdoor.com" + m.group(1) + ".htm"
    return cand if cand != cur_base else cur_base


def open_page(page, url: str, patience: int = 55) -> tuple[str | None, list]:
    """Navigate; wait out Turnstile. Returns (status, reviews|[]).

    status: "ok" | "login" | "blocked"
    """
    last_title = ""
    for attempt in range(3):
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
        except Exception as e:  # noqa: BLE001
            print(f"    goto err: {e}")
        deadline = time.time() + patience
        clicked = 0
        html = ""
        while time.time() < deadline:
            try:
                title = page.title()
                html = page.content()
                last_title = title
            except Exception:  # noqa: BLE001
                page.wait_for_timeout(1500)
                continue
            challenged = any(c in title for c in CHALLENGE)
            if not challenged:
                if any(t in title for t in LOGIN_TITLES):
                    return "login", []
                revs = extract_reviews(html)
                if revs is not None:
                    return "ok", revs
                if any(x in title for x in RATELIMIT):
                    # soft rate-limit interstitial — fail fast, let caller
                    # apply a cooldown instead of burning the full patience
                    return "ratelimited", []
            elif clicked < 3 and click_widget(page):
                clicked += 1
            page.wait_for_timeout(4000)
        if attempt < 2:
            backoff = 25 * (attempt + 1) + random.randint(0, 15)
            print(f"    retry after {backoff}s (attempt {attempt + 1} failed)")
            time.sleep(backoff)
    print(f"    open_page gave up; last_title={last_title!r} "
          f"final_url=...{page.url[-80:]!r}")
    return "blocked", []


def build_row(rev: dict, url: str, now: str) -> tuple[dict | None, str]:
    """Gates + row mapping. Returns (row|None, drop_reason)."""
    jt = ((rev.get("jobTitle") or {}).get("text") or "").strip()
    loc = ((rev.get("location") or {}).get("name") or "").strip()
    dt = (rev.get("reviewDateTime") or "").strip()
    summary = (rev.get("summary") or "").strip()
    pros = (rev.get("pros") or "").strip()
    cons = (rev.get("cons") or "").strip()
    company = ((rev.get("employer") or {}).get("shortName") or "").strip()

    if not dt.startswith(("2025", "2026")):
        return None, "drop_date"
    if not (CS_IT_RE.search(jt) and not CS_IT_EXCLUDE.search(jt)):
        return None, "drop_csit"
    if not is_ph_location(loc):
        return None, "drop_location"
    text = "\n".join(x for x in (summary, pros, cons) if x).strip()
    if not text:
        return None, "drop_text"
    if not company or not jt:
        return None, "drop_meta"

    # Stable id: Glassdoor reviewId keyed, so the same review seen via the
    # base URL and via filtered slice URLs collapses to one row.
    gd_id = str(rev.get("reviewId") or "").strip()
    id_key = f"gd:{gd_id}" if gd_id else url
    rating = rev.get("ratingOverall")
    return {
        "review_id": make_id(company, jt, dt, text, id_key),
        "company_name": company,
        "job_title": jt,
        "department": "",
        "seniority_level": "",
        "employment_status": str(rev.get("employmentStatus") or ""),
        "review_date": dt[:10],
        "rating": str(rating) if rating is not None else "",
        "review_text": summary,
        "pros": pros,
        "cons": cons,
        "location": loc,
        "source_platform": "Glassdoor",
        "source_url": url,
        "scraped_at": now,
    }, "kept"


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return default
    return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default=str(STORAGE / "gd_live_targets.json"))
    ap.add_argument("--staging", default=str(ROOT / "data" / "staging_glassdoor.csv"))
    ap.add_argument("--target-rows", type=int, default=600)
    ap.add_argument("--max-loads", type=int, default=0,
                    help="0 = unlimited (stop at target-rows)")
    ap.add_argument("--with-base", action="store_true",
                    help="also fetch the unfiltered company page once")
    ap.add_argument("--deep-base", action="store_true",
                    help="base page + overallRating slices (5 disjoint "
                         "newest-3 sets) — best for PH-heavy employers")
    args = ap.parse_args()

    targets = load_json(Path(args.targets), [])
    if not targets:
        print(f"no targets in {args.targets}")
        return 1
    staging = Path(args.staging)
    staging.parent.mkdir(exist_ok=True)
    done = set(load_json(STORAGE / "gd_live_done.json", []))
    pool_csit = load_json(STORAGE / "gd_live_pool_csit.json", {})

    # existing staging ids to avoid duplicate writes across resumes
    stage_ids: set[str] = set()
    if staging.exists():
        with open(staging, newline="", encoding="utf-8-sig") as f:
            stage_ids = {r["review_id"] for r in csv.DictReader(f)}
    n_existing = len(stage_ids)

    stats = {"kept": 0, "drop_date": 0, "drop_csit": 0, "drop_location": 0,
             "drop_text": 0, "drop_meta": 0, "dup": 0, "empty": 0,
             "login": 0, "blocked": 0, "loads": 0, "filter_lost": 0,
             "ratelimited": 0}
    new_file = not staging.exists()
    fh = open(staging, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(fh, fieldnames=COLUMNS)
    if new_file:
        writer.writeheader()

    profile = STORAGE / "browser_profile"
    print(f"[targets={len(targets)} done={len(done)} "
          f"staging_rows={n_existing} target={args.target_rows}]")

    with sync_playwright() as p:
        def launch():
            c = p.chromium.launch_persistent_context(
                str(profile), channel="chrome", headless=False,
                viewport={"width": 1280, "height": 900}, locale="en-US",
                args=["--disable-blink-features=AutomationControlled"],
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36"),
            )
            c.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                "window.chrome={runtime:{}};"
            )
            return c, (c.pages[0] if c.pages else c.new_page())

        ctx, page = launch()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")

        stop = False
        consec_blocked = 0
        crashes = 0
        rl_strikes = 0
        emp_csit = 0
        pool_seen = False

        defs: list = []
        if args.with_base or args.deep_base:
            defs.append(("base", None))
        if args.deep_base:
            defs += [("rating", r)
                     for r in ("ONE", "TWO", "THREE", "FOUR", "FIVE")]
        defs += [("title", t) for t in TITLES]

        def slice_url(base: str, kind: str, val) -> str:
            if kind == "base":
                return base
            if kind == "rating":
                return base + "?filter.overallRating=" + val
            return base + "?filter.jobTitleExact=" + quote(val)

        for ti in targets:
            if stop:
                break
            slug, eid = ti["slug"], ti["eid"]
            cur_base = BASE.format(slug=slug, eid=eid)
            emp_csit = pool_csit.get(slug, -1)  # -1 = pool never loaded fresh
            pool_seen = emp_csit >= 0
            pool_fresh = False
            for kind, val in defs:
                url = slice_url(cur_base, kind, val)
                tlabel = ("base" if kind == "base" else
                          f"rating:{val}" if kind == "rating" else val)
                if url in done:
                    continue
                if kind == "title" and pool_seen and emp_csit == 0:
                    print(f"    {ti['slug']}: skip title phase — no CS/IT "
                          f"reviews in base/rating pool")
                    break
                if stats["loads"] and args.max_loads and \
                        stats["loads"] >= args.max_loads:
                    stop = True
                    break
                if n_existing + stats["kept"] >= args.target_rows:
                    stop = True
                    break
                status, revs = "ratelimited", []
                rl_tries = 0
                while True:
                    try:
                        status, revs = open_page(page, url)
                    except Exception as e:  # noqa: BLE001 — browser died
                        crashes += 1
                        print(f"  BROWSER CRASH ({type(e).__name__}): {e}; "
                              f"relaunching [{crashes}/3]")
                        try:
                            ctx.close()
                        except Exception:  # noqa: BLE001
                            pass
                        time.sleep(8)
                        ctx, page = launch()
                        if crashes >= 3:
                            print("circuit breaker: 3 browser crashes — "
                                  "stopping (resumable)")
                            stop = True
                            break
                        continue  # retry same url after relaunch
                    if status != "ratelimited":
                        break
                    rl_tries += 1
                    stats["ratelimited"] += 1
                    rl_strikes += 1
                    if rl_tries >= 2 or rl_strikes >= 5:
                        break
                    cd = 180 if rl_tries == 1 else 420
                    print(f"  RATE LIMITED (try {rl_tries}/2, strikes "
                          f"{rl_strikes}/5) — cooldown {cd}s")
                    time.sleep(cd)
                if stop:
                    break
                if status == "ratelimited":
                    if rl_strikes >= 5:
                        print("  rate limit persists — circuit breaker: "
                              "stopping (resumable; url kept for resume)")
                        stop = True
                        break
                    lc = min(420 * rl_strikes, 900)
                    print(f"  RATE LIMIT on this url — long cooldown {lc}s "
                          f"(strikes {rl_strikes}/5), then next url")
                    time.sleep(lc)
                    continue  # url NOT marked done → resume retries it
                stats["loads"] += 1
                done.add(url)
                if status == "login":
                    stats["login"] += 1
                    consec_blocked = 0
                    rl_strikes = 0
                elif status == "blocked":
                    stats["blocked"] += 1
                    consec_blocked += 1
                    print(f"  BLOCKED {url} (consec={consec_blocked})")
                    if consec_blocked >= 5:
                        print("circuit breaker: 5 consecutive blocked pages "
                              "— stopping (resumable)")
                        stop = True
                        break
                    time.sleep(120 * consec_blocked)  # 120/240/360/480s ride-out
                else:
                    consec_blocked = 0
                    rl_strikes = 0
                    # redirect canonicalization: query-dropping 301s
                    new_base = canonical_base(page.url, cur_base)
                    if new_base != cur_base:
                        print(f"    canonicalized -> {new_base}")
                        cur_base = new_base
                    if kind != "base" and "filter." not in page.url:
                        stats["filter_lost"] += 1
                        print("    FILTER LOST (no filter param in final url)")
                    if kind != "title":
                        if not pool_fresh:
                            pool_fresh = True
                            emp_csit = 0  # fresh pool supersedes persisted count
                        pool_seen = True
                        for rev in revs:
                            jt = ((rev.get("jobTitle") or {}).get("text") or "")
                            if (CS_IT_RE.search(jt)
                                    and not CS_IT_EXCLUDE.search(jt)):
                                emp_csit += 1
                        pool_csit[slug] = emp_csit
                        save_json(STORAGE / "gd_live_pool_csit.json", pool_csit)
                    if not revs:
                        stats["empty"] += 1
                    for rev in revs:
                        row, why = build_row(rev, url, now)
                        if row is None:
                            stats[why] += 1
                            continue
                        if row["review_id"] in stage_ids:
                            stats["dup"] += 1
                            continue
                        writer.writerow(row)
                        stage_ids.add(row["review_id"])
                        stats["kept"] += 1
                    fh.flush()
                    titles = [((r.get("jobTitle") or {}).get("text") or "?")[:24]
                              for r in revs[:3]]
                    print(f"    {ti['slug']} [{tlabel}]: revs={len(revs)} "
                          f"kept={stats['kept']} titles={titles}")
                if stats["loads"] % 10 == 0:
                    save_json(STORAGE / "gd_live_done.json", sorted(done))
                    total = n_existing + stats["kept"]
                    print(f"[loads={stats['loads']}/{len(targets)}x{len(defs)}] "
                          f"total={total} kept={stats['kept']} "
                          f"date={stats['drop_date']} csit={stats['drop_csit']} "
                          f"loc={stats['drop_location']} empty={stats['empty']} "
                          f"login={stats['login']} blocked={stats['blocked']} "
                          f"filtlost={stats['filter_lost']} "
                          f"rl={stats['ratelimited']}")
                time.sleep(6 + random.uniform(0, 3))

        try:
            ctx.close()
        except Exception:  # noqa: BLE001
            pass
    fh.close()
    save_json(STORAGE / "gd_live_done.json", sorted(done))
    total = n_existing + stats["kept"]
    print(f"\nFINAL: staging_total={total} new_kept={stats['kept']} "
          f"stats={json.dumps(stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
