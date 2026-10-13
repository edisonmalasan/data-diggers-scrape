"""Merge data/staging_*.csv (per-source subagent/scrapers) into
data/job_reviews_raw.csv — append-only, dedupe by review_id, contract gates.

Safe to run while scrapers hold their own file handles open for append:
this script rewrites only at the end, in one shot, and is idempotent.

Usage:  python scripts/job_reviews/merge_staging.py [--purge]

--purge deletes the staging/member CSVs after a successful merge pass,
leaving data/job_reviews_raw.csv + .md as the only deliverables. If a
running scraper still holds a file open, the delete is skipped safely.
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
from pathlib import Path

from scrape_jobstreet import (COLUMNS, CS_IT_EXCLUDE, CS_IT_RE,
                              is_ph_location)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "job_reviews_raw.csv"
# team-member contribution files (17-col supersets; extras projected away)
EXTRA_FILES = [ROOT / "data" / "job_reviews_2025_2026.csv",
               ROOT / "data" / "job_reviews_2026_expanded_partial.csv"]

REQUIRED = ["company_name", "job_title", "review_date",
            "location", "source_platform", "source_url"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--purge", action="store_true",
                    help="delete staging/member CSVs after merging "
                         "(raw stays the single source of truth)")
    args = ap.parse_args()
    staging_files = sorted(glob.glob(str(ROOT / "data" / "staging_*.csv")))
    for e in EXTRA_FILES:
        if e.exists():
            staging_files.append(str(e))
    if not staging_files:
        print(f"no staging files at {ROOT / 'data' / 'staging_*.csv'} "
              "— nothing to merge")
        return 0
    with open(RAW, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    seen = {r["review_id"] for r in rows}
    seen_content = {
        ((r.get("company_name") or "").lower(),
         (r.get("job_title") or "").lower(),
         (r.get("review_date") or ""),
         (r.get("review_text") or "")[:120].lower())
        for r in rows
    }

    added = skipped_dup = dropped = 0
    for sf in staging_files:
        with open(sf, newline="", encoding="utf-8-sig") as f:
            staging = list(csv.DictReader(f))
        n_added = 0
        for r in staging:
            r = {k: (r.get(k) or "").strip() for k in COLUMNS}
            text = (r["review_text"] + r["pros"] + r["cons"]).strip()
            content = (r["company_name"].lower(), r["job_title"].lower(),
                       r["review_date"], r["review_text"][:120].lower())
            title_ok = (CS_IT_RE.search(r["job_title"])
                        and not CS_IT_EXCLUDE.search(r["job_title"]))
            if (not r["review_id"] or r["review_id"] in seen
                    or content in seen_content
                    or not any(y in r["review_date"] for y in ("2025", "2026"))
                    or not text
                    or any(not r[c] for c in REQUIRED)
                    or not title_ok
                    or not is_ph_location(r["location"])):
                if r["review_id"] in seen or content in seen_content:
                    skipped_dup += 1
                else:
                    dropped += 1
                continue
            rows.append(r)
            seen.add(r["review_id"])
            seen_content.add(content)
            added += 1
            n_added += 1
        print(f"  {Path(sf).name}: {len(staging)} rows -> +{n_added}")

    if added:
        with open(RAW, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
    print(f"staging_files={len(staging_files)} added={added} "
          f"dup={skipped_dup} dropped(gate-fail)={dropped} "
          f"total={len(rows)}")
    if args.purge:
        for sf in staging_files:
            try:
                Path(sf).unlink()
                print(f"  purged {Path(sf).name}")
            except OSError as e:
                print(f"  purge skipped {Path(sf).name}: {e.strerror or e} "
                      "(will retry next checkpoint)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
