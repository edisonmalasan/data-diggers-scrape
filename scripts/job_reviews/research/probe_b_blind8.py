"""Phase 24: Blind — probe candidate company slugs (PH-heavy employers) + robots.txt."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def facets(html: str, key: str) -> list[dict]:
    un = html.replace('\\"', '"').replace("\\n", "\n")
    i = un.find('"' + key + '":[')
    if i < 0:
        return []
    j = un.index("[", i)
    depth = 0
    for k in range(j, len(un)):
        if un[k] == "[":
            depth += 1
        elif un[k] == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(un[j:k + 1])
                except json.JSONDecodeError:
                    return []
    return []


CANDIDATES = [
    "Accenture", "Concentrix", "Teleperformance", "IBM", "JPMorgan-Chase",
    "JPMorgan-Chase-Co", "HSBC", "Capital-One", "DXC-Technology", "Globe-Telecom",
    "Ayala", "Convergys", "Teleperformance-Philippines", "Shell", "Tokyo-Mitsubishi-UFJ",
    "Infosys", "Wipro", "Cognizant", "Capgemini", "Optum", "UnitedHealth-Group",
    "Deutsche-Bank", "Citi", "Citibank", "Wells-Fargo", "American-Express",
]


def main() -> int:
    f = Fetcher("blind")
    results = []
    try:
        # robots.txt first (browser-like accept)
        r = f.get("https://www.teamblind.com/robots.txt", allow="text/plain,*/*",
                  stream_to=STORAGE / "robots_blind.txt")
        print("robots:", r.status_code, repr(r.text[:400]))
    except StopSite as e:
        print("STOPPED", e)
        return 0

    try:
        for slug in CANDIDATES:
            u = f"https://www.teamblind.com/company/{slug}/reviews"
            r = f.get(u, timeout=30)
            title = ""
            m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()[:70]
            if r.status_code != 200 or "reviews" not in title.lower():
                print(f"{slug}: MISS {r.status_code} {title!r}")
                continue
            cc = facets(r.text, "locationCityCounts")
            total_m = re.search(r'"total":(\d+)', r.text.replace('\\"', '"'))
            total = total_m.group(1) if total_m else "?"
            (STORAGE / f"blind_co_{slug}.html").write_text(r.text, encoding="utf-8")
            print(f"{slug}: OK total={total} cities={len(cc)} | {title}")
            results.append((slug, total, cc))
    except StopSite as e:
        print("STOPPED", e)

    # PH-relevant facet keys per company
    PH_KEYS = ["manila", "makati", "taguig", "pasig", "cebu", "davao", "iloilo",
               "philippin", "bgc", "bonifacio", "alabang", "clark", "subic",
               "mandaluyong", "quezon city", "pasay", "antipolo", "calamba",
               "muntinlupa", "paranaque", "bacolod", "cebu city", "davao city"]
    print("\n== PH facet keys ==")
    for slug, total, cc in results:
        ph = [c for c in cc if any(k in c["key"].lower() for k in PH_KEYS)]
        if ph:
            print(f"  {slug} (total {total}): {ph}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
