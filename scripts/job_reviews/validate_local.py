"""Local validation: parse saved Indeed HTML dumps with the real extraction
pipeline (extract_items + build_row), no network. Confirms the PH/CS-IT/date
gates and shows exactly why rows pass or fail.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scrape_indeed_wb import build_row, extract_items  # noqa: E402

DUMP = Path(r"C:\Users\Edison\AppData\Local\Temp\opencode")
SNAPS = {
    "indep_iqor_list.html": "https://web.archive.org/web/20260105id_/https://ph.indeed.com/cmp/Iqor/reviews/",
    "indep_keyence_list.html": "https://web.archive.org/web/20260424id_/https://ph.indeed.com/cmp/Keyence/reviews",
    "indep_yellowbrick_perma1.html": "https://web.archive.org/web/20260701id_/https://ph.indeed.com/cmp/Yellow-Brick-Road-Productions/reviews/x",
    "indep_coherent_list.html": "https://web.archive.org/web/20260522id_/https://ph.indeed.com/cmp/Coherent-Corp.-1/reviews",
    "indep_grandapex_list.html": "https://web.archive.org/web/20260113id_/https://ph.indeed.com/cmp/Grand-Apex-Construction-Inc./reviews",
}

total_items = total_kept = 0
for fname, snap in SNAPS.items():
    f = DUMP / fname
    if not f.exists():
        print(f"[skip] {fname} not present")
        continue
    html = f.read_text(encoding="utf-8")
    items = extract_items(html)
    if items is None:
        print(f"[{fname}] extract_items -> None (no initialData payload)")
        continue
    stats = {"items": 0, "drop_date": 0, "drop_text": 0, "drop_csit": 0,
             "drop_country": 0, "drop_location": 0, "drop_meta": 0}
    kept = 0
    print(f"\n=== {fname}: {len(items)} item(s) ===")
    for raw in items:
        raw["host"] = "ph.indeed.com"
        row = build_row(raw, snap, "2026-10-09T00:00:00+00:00", stats)
        if row:
            kept += 1
            print(f"  KEEP | {row['company_name'][:22]:22} | {row['job_title'][:26]:26} | "
                  f"{row['review_date']:16} | {row['location'][:20]:20} | {row['employment_status']}")
    print(f"  gate funnel: {stats}")
    total_items += len(items)
    total_kept += kept

print(f"\n==== TOTAL items={total_items} kept={total_kept} ====")
