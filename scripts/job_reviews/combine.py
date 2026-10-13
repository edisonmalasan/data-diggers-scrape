"""Merge per-member CSVs (data/incoming/*.csv) into data/job_reviews_raw.csv.

Usage:  python scripts/job_reviews/combine.py
Each incoming file must carry the 15 contract headers (copy the header line
from data/job_reviews_raw.csv). Missing review_id values are generated.
Rows violating the contract (no 2026 date, no text, missing required field)
are dropped and REPORTED per file — fix and re-run, it is idempotent.

Then: python scripts/job_reviews/to_markdown.py && python scripts/job_reviews/validate.py
"""

from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INCOMING = ROOT / "data" / "incoming"
OUT_CSV = ROOT / "data" / "job_reviews_raw.csv"
COLUMNS = [
    "review_id", "company_name", "job_title", "department",
    "seniority_level", "employment_status", "review_date", "rating",
    "review_text", "pros", "cons", "location",
    "source_platform", "source_url", "scraped_at",
]
REQUIRED = ["company_name", "job_title", "review_date",
            "location", "source_platform", "source_url"]


def make_id(company: str, title: str, date: str, text: str, url: str) -> str:
    raw = "|".join([company, title, date, text[:120], url]).encode()
    return "rv_" + hashlib.sha1(raw).hexdigest()[:12]


def main() -> int:
    files = sorted(INCOMING.glob("*.csv")) if INCOMING.is_dir() else []
    if not files:
        print(f"Nothing to merge: put member files in {INCOMING} (e.g. malasan.csv).")
        return 1
    # Seed with rows already in the output CSV so re-running combine.py
    # never wipes previously scraped data (dedupe by review_id).
    merged: dict[str, dict] = {}
    if OUT_CSV.exists():
        with open(OUT_CSV, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                rid = (r.get("review_id") or "").strip()
                if rid:
                    merged[rid] = {k: (r.get(k) or "") for k in COLUMNS}
        print(f"existing rows loaded from {OUT_CSV.name}: {len(merged)}")
    for f in files:
        with open(f, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        kept = dropped = 0
        for r in rows:
            text = (r.get("review_text") or "") + (r.get("pros") or "") + (r.get("cons") or "")
            if (not text.strip() or "2026" not in (r.get("review_date") or "")
                    or any(not (r.get(c) or "").strip() for c in REQUIRED)):
                dropped += 1
                continue
            r = {k: (r.get(k) or "").strip() for k in COLUMNS}
            if not r["review_id"]:
                r["review_id"] = make_id(r["company_name"], r["job_title"],
                                         r["review_date"], r["review_text"], r["source_url"])
            if not r["scraped_at"]:
                r["scraped_at"] = datetime.now(timezone.utc).isoformat()
            if r["review_id"] not in merged:
                merged[r["review_id"]] = r
                kept += 1
        print(f"{f.name}: kept={kept} dropped(non-2026/incomplete)={dropped}")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(merged.values())
    print(f"MERGED {len(merged)} unique rows -> {OUT_CSV}")
    print("Next: python scripts/job_reviews/to_markdown.py && python scripts/job_reviews/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
