"""Drop rows whose location is explicitly non-PH (contract rule 3).

Used as a final/periodic scrub: scrapers now gate with is_ph_location(),
but rows collected before that fix (or by third-party scrapers) may
contain foreign locations (e.g. "Los Angeles, CA").
"""
import csv
import re
from pathlib import Path

NON_PH = re.compile(
    r",\s*(A[LKSZEP]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CHJMV]|O[KR]|"
    r"P[AR]|RI|S[CD]|T[NX]|UT|V[TFA]|W[AVY])\.?\s*$"
    r"|\bunited states\b|\busa\b|\bcalifornia\b|los angeles|new york|"
    r"\bsingapore\b|\bindia\b|\bmalaysia\b|\bindonesia\b|\bvietnam\b|\bthailand\b", re.I)

p = Path(__file__).resolve().parents[2] / "data" / "job_reviews_raw.csv"
rows = list(csv.DictReader(p.open(newline="", encoding="utf-8")))
bad = [r for r in rows if NON_PH.search(r.get("location") or "")]
print(f"total={len(rows)} non_PH={len(bad)}")
for r in bad:
    print("  DROP:", r["review_id"], "|", r["company_name"], "|",
          r["location"], "|", r["source_platform"])
kept = [r for r in rows if not NON_PH.search(r.get("location") or "")]
if bad:
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(kept)
print(f"kept={len(kept)}")
