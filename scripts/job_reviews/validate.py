"""Validate ./data/job_reviews_raw.csv against docs/DATA_CONTRACT.md section 3.

Usage:  python scripts/job_reviews/validate.py
Exit 0 = pass (or pass with warnings); exit 1 = fail.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

CSV = Path(__file__).resolve().parents[2] / "data" / "job_reviews_raw.csv"
REQUIRED = ["review_id", "company_name", "job_title", "review_date",
            "location", "source_platform", "source_url", "scraped_at"]


def main() -> int:
    if not CSV.exists():
        print(f"FAIL: {CSV} not found. Run collect.py first.")
        return 1
    with open(CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    errors: list[str] = []
    if not rows:
        print("PASS (empty): header OK, 0 rows — run collect.py to fill (min 200).")
        return 0
    ids = [r.get("review_id", "") for r in rows]
    if len(set(ids)) != len(ids):
        errors.append(f"rule 1: duplicate review_id ({len(ids) - len(set(ids))} dups)")
    bad_date = [i for i, r in enumerate(rows)
                if not any(y in (r.get("review_date") or "") for y in ("2025", "2026"))]
    if bad_date:
        errors.append(f"rule 2: {len(bad_date)} rows lack 2025/2026 review_date (e.g. row {bad_date[0] + 2})")
    missing_req = [i for i, r in enumerate(rows)
                   if any(not (r.get(c) or "").strip() for c in REQUIRED)]
    if missing_req:
        errors.append(f"required fields: {len(missing_req)} rows missing a required field")
    no_text = [i for i, r in enumerate(rows)
               if not ((r.get("review_text") or "").strip()
                       or (r.get("pros") or "").strip()
                       or (r.get("cons") or "").strip())]
    if no_text:
        errors.append(f"rule 4: {len(no_text)} rows with no review_text/pros/cons")
    no_url = [i for i, r in enumerate(rows) if not (r.get("source_url") or "").startswith("http")]
    if no_url:
        errors.append(f"traceability: {len(no_url)} rows without http source_url")
    # rule 3: PH employment — reject explicit non-PH locations (e.g. "Los Angeles, CA")
    import re as _re
    non_ph = [i for i, r in enumerate(rows)
              if _re.search(
                  r",\s*(A[LKSZEP]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|"
                  r"N[CHJMV]|O[KR]|P[AR]|RI|S[CD]|T[NX]|UT|V[TFA]|W[AVY])\.?\s*$"
                  r"|\bunited states\b|\busa\b|\bcalifornia\b|los angeles|new york|"
                  r"\bsingapore\b|\bindia\b|\bmalaysia\b|\bindonesia\b|\bvietnam\b|\bthailand\b",
                  (r.get("location") or ""), _re.I)]
    if non_ph:
        errors.append(f"rule 3: {len(non_ph)} rows with non-PH location (e.g. row {non_ph[0] + 2})")
    print(f"rows={len(rows)} unique_ids={len(set(ids))} errors={len(errors)}")
    for e in errors:
        print("FAIL:", e)
    if len(rows) < 200:
        print(f"WARN: {len(rows)}/200 minimum (contract acceptance criteria) — keep collecting.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
