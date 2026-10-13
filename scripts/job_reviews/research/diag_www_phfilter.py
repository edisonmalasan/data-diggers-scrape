"""Narrow CDX probes: do ANY www.indeed.com captures carry PH country/location
filters for PH-relevant employers?  Full-domain regex probes 504; per-company
prefix queries are cheap. Read-only."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from scrape_indeed_wb import cdx_query  # noqa: E402

COMPANIES = [
    "Accenture", "Concentrix", "Cognizant", "Teleperformance", "TaskUs",
    "Iqor", "Vxi-Global-Solutions", "IBM", "Globe-Telecom", "PLDT",
    "Teleperformance", "Genpact", "Infosys", "Wipro", "Tata-Consultancy-Services",
    "Convergys", "Alorica", "Sykes", "Telus-International", "Shopee",
    "Jollibee", "Unionbank", "Bdo", "Ayala", "Manulife", "Optum",
    "Globant", "EPAM", "Everise", "51Talk", "Microsourcing",
]

FILTERS = {
    "fcountry=PH": r"original:.*fcountry=PH.*",
    "floc=PH-city": r"original:.*floc=(Manila|Makati|Taguig|Quezon|Cebu|Davao|Pasig|Philippines).*",
}


def main() -> int:
    total = 0
    for co in COMPANIES:
        prefix = f"www.indeed.com/cmp/{co}/reviews"
        for name, filt in FILTERS.items():
            rows = cdx_query({"url": prefix, "filter": ["statuscode:200", filt],
                              "fl": "original,timestamp", "limit": "200"},
                             tries=2)
            if rows:
                total += len(rows)
                print(f"[HIT] {co} {name}: {len(rows)}")
                for r in rows[:6]:
                    print("     ", r[1], r[0][:130])
            else:
                print(f"[   ] {co} {name}: 0")
            time.sleep(2.5)
    print(f"\ntotal www PH-filter captures: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
