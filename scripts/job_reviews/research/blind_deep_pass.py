# -*- coding: utf-8 -*-
"""Blind deep pass: page PH-facet companies' reviews until the pre-2026 boundary,
apply contract gates in order, stage survivors to data/staging_blind.csv.

Gates/columns/make_id imported from scrape_jobstreet.py (never edited).
Politeness via siteb_lib.Fetcher (2-3s delay, backoff cap 60s, 8-failure breaker).
No login, no CAPTCHA, no blocked domains.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime
from urllib.parse import quote

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from blind_extract import extract_reviews, extract_total
from scrape_jobstreet import (COLUMNS, CS_IT_EXCLUDE, CS_IT_RE, is_ph_location,
                              make_id)
from siteb_lib import STORAGE, Fetcher, StopSite

STAGING = os.path.join(os.path.dirname(os.path.dirname(HERE)), "data",
                       "staging_blind.csv")
RESULTS = STORAGE / "blind_deep_results.json"
SOURCE_PLATFORM = "Blind"
MAX_FETCHES = 700
WALL_SECS = 45 * 60

# (slug, total_from_page1, ph_facet_count_from_prior_filteredCount_metadata)
COMPANIES = [
    ("Manulife", 27, 1),          # known 2023 PH review -> cheap full-coverage sanity check
    ("Accenture", 1340, 4),
    ("Optum", 559, 2),
    ("Analog-Devices", 222, 1),
    ("Citi", 711, 1),
    ("Wells-Fargo", 635, 1),
    ("EY", 811, 1),
    ("Grab", 927, 1),
    ("IBM", 2147, 2),
    ("JPMorgan", 2494, 1),
    ("Oracle", 3136, 1),
    ("Cisco", 2792, 1),
    ("Google", None, 2),
    ("Microsoft", 12994, 3),
    ("Amazon", 31378, 1),
]

t0 = time.time()
fetcher = Fetcher("blinddeep", max_requests=MAX_FETCHES, delay=2.5)


def elapsed() -> float:
    return time.time() - t0


def out_of_time() -> bool:
    return elapsed() > WALL_SECS or fetcher.n >= MAX_FETCHES - 2


seen: dict[str, dict] = {}          # review id -> review (verbatim)
staged_ids: set[str] = set()
stats = {"pages": 0, "companies_done": [], "companies_partial": [],
         "companies_not_started": [], "per_company": {}}
funnel = {"unique": 0, "gate_2026": 0, "gate_csit": 0, "gate_ph": 0,
          "gate_text": 0, "staged": 0}
ph_any_year: list[dict] = []

# in-session dedupe must also respect rows already in the staging file
if os.path.exists(STAGING):
    with open(STAGING, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            staged_ids.add(row["review_id"])


def save_results() -> None:
    RESULTS.write_text(json.dumps({
        "elapsed_sec": round(elapsed(), 1),
        "fetches": fetcher.n,
        "stats": stats,
        "funnel": funnel,
        "ph_any_year": ph_any_year,
    }, indent=1, ensure_ascii=False), encoding="utf-8")


def stage(rows: list[dict]) -> None:
    if not rows:
        return
    new_file = not os.path.exists(STAGING)
    with open(STAGING, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow(r)
        f.flush()
    print("  STAGED %d rows -> %s" % (len(rows), STAGING), flush=True)


def gate_and_stage(slug: str, page_url: str) -> None:
    """Apply gates IN ORDER to reviews newly seen for this company."""
    new = [r for r in seen.values() if r.get("_company_slug") == slug and not r.get("_gated")]
    funnel["unique"] += len(new)
    kept = []
    for r in new:
        r["_gated"] = True
        d = (r.get("createdAt") or "")[:10]
        if not any(y in d for y in ("2025", "2026")):
            continue
        funnel["gate_2026"] += 1
        title = (r.get("jobgroup") or "").strip()
        if not title or not CS_IT_RE.search(title) or CS_IT_EXCLUDE.search(title):
            continue
        funnel["gate_csit"] += 1
        loc = (r.get("memberLocation") or "").strip()
        iso = r.get("memberLocationCountryIsoCode") or ""
        if not (is_ph_location(loc) and iso == "PH"):
            continue
        funnel["gate_ph"] += 1
        ph_any_year.append({"company": r.get("companyName"), "job": title,
                            "date": d, "loc": loc, "iso": iso,
                            "id": r.get("id"), "alias": r.get("urlAlias")})
        text = (r.get("summary") or "").strip()
        pros = (r.get("pros") or "").strip()
        cons = (r.get("cons") or "").strip()
        if not (text or pros or cons):
            continue
        funnel["gate_text"] += 1
        rid = make_id(r.get("companyName") or "", title, d, text,
                      "blind:%s" % r.get("id"))
        if rid in staged_ids:
            continue
        staged_ids.add(rid)
        kept.append({
            "review_id": rid,
            "company_name": r.get("companyName") or "",
            "job_title": title,
            "department": "",
            "seniority_level": "",
            "employment_status": "",
            "review_date": d,
            "rating": str(r.get("overall") or ""),
            "review_text": text,
            "pros": pros,
            "cons": cons,
            "location": loc,
            "source_platform": SOURCE_PLATFORM,
            "source_url": page_url,
            "scraped_at": datetime.now().isoformat(timespec="seconds"),
        })
    funnel["staged"] += len(kept)
    stage(kept)


for slug, total, phcnt in COMPANIES:
    if out_of_time():
        stats["companies_not_started"].append(slug)
        continue
    cs = {"pages": 0, "reviews": 0, "boundary": None, "total": total}
    page = 1
    first_ids: set[str] = set()
    print("== %s (total=%s, ph_facet=%s)" % (slug, total, phcnt), flush=True)
    try:
        while not out_of_time():
            url = ("https://www.teamblind.com/company/%s/reviews?page=%d"
                   % (quote(slug), page))
            r = fetcher.get(url)
            if r.status_code != 200:
                cs["boundary"] = "http_%d" % r.status_code
                break
            revs = extract_reviews(r.text)
            if not revs:
                cs["boundary"] = "exhausted"
                break
            page_ids = set()
            for rev in revs:
                rid = str(rev.get("id"))
                page_ids.add(rid)
                if rid not in seen:
                    rev["_company_slug"] = slug
                    seen[rid] = rev
            if page == 1:
                first_ids = page_ids
            if page == 2 and first_ids and page_ids <= first_ids:
                cs["boundary"] = "pagination_broken"
                print("  pagination no-op at page 2 — stopping company", flush=True)
                break
            stats["pages"] += 1
            cs["pages"] += 1
            maxdate = max((rev.get("createdAt") or "")[:10] for rev in revs)
            if maxdate < "2025-01-01":
                cs["boundary"] = "pre_2025"
                break
            page += 1
    except StopSite as e:
        cs["boundary"] = "stop:%s" % e
        stats["companies_partial"].append(slug)
        gate_and_stage(slug, "https://www.teamblind.com/company/%s/reviews" % slug)
        stats["per_company"][slug] = cs
        save_results()
        print("STOP: %s" % e, flush=True)
        break
    cs["reviews"] = sum(1 for v in seen.values() if v.get("_company_slug") == slug)
    gate_and_stage(slug, "https://www.teamblind.com/company/%s/reviews" % slug)
    stats["per_company"][slug] = cs
    if cs["boundary"] in ("exhausted", "pre_2025"):
        stats["companies_done"].append(slug)
    else:
        stats["companies_partial"].append(slug)
    save_results()
    print("  done: pages=%d revs=%d boundary=%s fetches=%d elapsed=%.0fs"
          % (cs["pages"], cs["reviews"], cs["boundary"], fetcher.n, elapsed()),
          flush=True)

# remaining companies never started
done_or_partial = set(stats["companies_done"]) | set(stats["companies_partial"])
for slug, _, _ in COMPANIES:
    if slug not in done_or_partial and slug not in stats["companies_not_started"]:
        stats["companies_not_started"].append(slug)

# PH reviews at any year (context for the scarcest-gate statement)
for v in seen.values():
    if (v.get("memberLocationCountryIsoCode") == "PH"
            and is_ph_location(v.get("memberLocation") or "")):
        entry = {"company": v.get("companyName"), "job": v.get("jobgroup"),
                 "date": (v.get("createdAt") or "")[:10],
                 "loc": v.get("memberLocation"), "id": v.get("id")}
        if entry not in ph_any_year and all(entry["id"] != p["id"] for p in ph_any_year):
            ph_any_year.append(entry)

save_results()
print()
print("==== FINAL ====", flush=True)
print("fetches=%d elapsed=%.0fmin" % (fetcher.n, elapsed() / 60))
print("funnel:", json.dumps(funnel))
print("done:", stats["companies_done"])
print("partial:", stats["companies_partial"])
print("not started:", stats["companies_not_started"])
print("PH reviews found (any year):", json.dumps(ph_any_year, ensure_ascii=False))
