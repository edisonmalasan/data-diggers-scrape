"""Strip leaked JobStreet UI fragments (Helpful?, 'N person', Show more...)
from pros/cons/review_text in data/job_reviews_raw.csv.

Non-destructive: only lines that are pure UI junk are removed; content is
untouched and review_id is NOT recomputed (dedupe already happened).
Run after every collection pass; safe to re-run.
"""
import csv
import re
from pathlib import Path

CSV = Path(__file__).resolve().parents[2] / "data" / "job_reviews_raw.csv"

UI_LINE = re.compile(
    r"^(Helpful\??|Show (?:more|less)|Read (?:more|less)|Prev|Next|Flag|"
    r"\d+\s*(?:person|people)(?:\s+found\s+this\s+helpful)?|"
    r"found this helpful)\s*$",
    re.I,
)


def clean_field(v: str) -> str:
    if not v:
        return v
    lines = [l.rstrip() for l in v.split("\n") if not UI_LINE.match(l.strip())]
    out = "\n".join(lines).strip()
    out = re.sub(r"[ \t]*\bHelpful\?\s*$", "", out)   # glued to a content line
    return out.strip()


def main() -> None:
    with open(CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("no rows")
        return
    changed = 0
    for r in rows:
        for field in ("pros", "cons", "review_text"):
            new = clean_field(r.get(field, ""))
            if new != r.get(field, ""):
                r[field] = new
                changed += 1
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"OK: {len(rows)} rows, {changed} field(s) cleaned -> {CSV}")


if __name__ == "__main__":
    main()
