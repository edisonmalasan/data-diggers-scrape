"""Inspect saved Indeed dumps: country / submissionDate / jobTitle values."""
import collections
import re
from pathlib import Path

STORAGE = Path(__file__).resolve().parents[1] / ".storage"

COUNTRY_RE = re.compile(r'[&"]country[&"]:\s*[&"]([^&"]{0,30})[&"]')
DATE_RE = re.compile(r'[&"]submissionDate[&"]:\s*[&"]([^&"]{0,40})[&"]')
TITLE_RE = re.compile(r'[&"]jobTitle[&"]:\s*[&"]([^&"]{0,80})[&"]')

for name in ["indeed_coherent_filtered.html", "indeed_keyence_single.html"]:
    p = STORAGE / name
    if not p.exists():
        print(f"{name}: MISSING")
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    countries = collections.Counter(COUNTRY_RE.findall(t))
    dates = collections.Counter(DATE_RE.findall(t))
    titles = TITLE_RE.findall(t)
    print(f"\n=== {name} ({len(t)} bytes) ===")
    print(f"country: {dict(countries)}")
    d2026 = [d for d in dates if '2026' in d]
    print(f"submissionDate: total={sum(dates.values())} 2026={len(d2026)} "
          f"sample={list(dates)[:6]}")
    print(f"jobTitle sample: {titles[:12]}")
