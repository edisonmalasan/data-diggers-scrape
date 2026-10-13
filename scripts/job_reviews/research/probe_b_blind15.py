"""Phase 31: Blind — probe candidate company slugs; report total reviews, PH facet
count, and whether PH is selectable in the location dropdown."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blind_extract import extract_facets, extract_total, flight_strings  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

SLUGS = [
    "JPMorgan", "Chase", "Bank-of-America", "Goldman-Sachs", "Morgan-Stanley",
    "Standard-Chartered", "Barclays", "UBS", "Deloitte", "PwC", "EY", "KPMG",
    "Genpact", "TaskUs", "Alorica", "Foundever", "TELUS-International", "iHerb",
    "Shopee", "Grab", "Sea-Limited", "MetLife", "Manulife", "Cigna", "Aetna",
    "Humana", "Dell", "HPE", "Intel", "Texas-Instruments", "Analog-Devices",
    "NXP", "Motorola-Solutions", "Cisco", "Amazon", "Microsoft", "Oracle",
    "Salesforce", "Sykes", "Sutherland", "WNS",
]


def main() -> int:
    f = Fetcher("blind")
    hits = []
    try:
        for slug in SLUGS:
            u = f"https://www.teamblind.com/company/{slug}/reviews"
            r = f.get(u, timeout=30)
            m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:60] if m else ""
            if r.status_code != 200 or "Review" not in title:
                print(f"{slug}: MISS {r.status_code}")
                continue
            total = extract_total(r.text)
            cc = extract_facets(r.text, "locationCountryCounts")
            ph = next((c["docCount"] for c in cc if c.get("key") == "Philippines"), 0)
            blob = "\n".join(flight_strings(r.text))
            ph_in_dd = '"location":"PH"' in blob
            (STORAGE / f"blind_co_{slug}.html").write_text(r.text, encoding="utf-8")
            print(f"{slug}: total={total} PH={ph} PH_dropdown={ph_in_dd} | {title}")
            if ph:
                hits.append((slug, total, ph, ph_in_dd))
    except StopSite as e:
        print("STOPPED", e)
    print("\n== companies with PH reviews ==")
    for h in hits:
        print("   ", h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
