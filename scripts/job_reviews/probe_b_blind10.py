"""Phase 26: Blind — verify ?location param on Accenture with known facet keys."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blind_extract import extract_facets, extract_reviews, extract_total  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def main() -> int:
    h = (STORAGE / "blind_co_Accenture.html").read_text(encoding="utf-8", errors="replace")
    cc = extract_facets(h, "locationCityCounts")
    print("Accenture city facet top10:", cc[:10])

    f = Fetcher("blind")
    tests = ["India", "United%20States", "Philippines", "Philippines%2C"]
    try:
        for val in tests:
            u = f"https://www.teamblind.com/company/Accenture/reviews?location={val}"
            r = f.get(u, timeout=30, stream_to=STORAGE / f"blind_accloc_{val[:12]}.html")
            rs = extract_reviews(r.text)
            locs = sorted({x.get("memberLocation") or "?" for x in rs})
            print(f"location={val}: total={extract_total(r.text)} n={len(rs)} distinct_locs={locs[:8]}")
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
