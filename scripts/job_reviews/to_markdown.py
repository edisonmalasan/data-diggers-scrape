"""Regenerate data/job_reviews_raw.md as ONE markdown table from the CSV.

Usage:  python scripts/job_reviews/to_markdown.py
Run after every collect.py run. Never hand-edit the .md.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "data" / "job_reviews_raw.csv"
MD = ROOT / "data" / "job_reviews_raw.md"


def cell(v: str) -> str:
    return (v or "").replace("|", "\\|").replace("\n", "<br>")


def main() -> int:
    if not CSV.exists():
        print(f"FAIL: {CSV} not found.")
        return 1
    with open(CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        rows = list(reader)
    lines = ["| " + " | ".join(cols) + " |",
             "| " + " | ".join(["---"] * len(cols)) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(cell(r.get(c, "")) for c in cols) + " |")
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: {len(rows)} rows -> {MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
