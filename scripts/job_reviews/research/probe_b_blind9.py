"""Phase 25: Blind — review permalink format, country facets, and PH filter test."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blind_extract import extract_facets, extract_reviews, extract_total  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

PH_KEY = re.compile(r"philippin|manila|makati|taguig|pasig|cebu|davao|iloilo|bgc|"
                    r"bonifacio|alabang|clark|subic|mandaluyong|quezon|pasay|bacolod",
                    re.I)


def main() -> int:
    # 1) permalink format
    h = (STORAGE / "blind_co_Accenture.html").read_text(encoding="utf-8", errors="replace")
    hrefs = sorted(set(re.findall(r'href="([^"]*reviews[^"]*)"', h)))
    print("review hrefs sample:", [x for x in hrefs if "/company/Accenture" in x][:8])
    alias = re.findall(r'"urlAlias":"([^"]+)"', h)
    print("urlAlias sample:", alias[:8])

    # 2) country facets on every saved company page
    print("\n== saved company pages: PH counts ==")
    for p in sorted(STORAGE.glob("blind_co_*.html")):
        hh = p.read_text(encoding="utf-8", errors="replace")
        cc = extract_facets(hh, "locationCityCounts")
        nc = extract_facets(hh, "locationCountryCounts")
        ph_c = [x for x in cc if PH_KEY.search(x.get("key", ""))]
        ph_n = [x for x in nc if PH_KEY.search(x.get("key", ""))]
        if ph_c or ph_n:
            print(f"  {p.stem.replace('blind_co_', '')}: city={ph_c} country={ph_n}")

    # 3) PH filter on Accenture
    f = Fetcher("blind")
    try:
        u = "https://www.teamblind.com/company/Accenture/reviews?location=Philippines"
        r = f.get(u, timeout=30, stream_to=STORAGE / "blind_acc_ph.html")
        rs = extract_reviews(r.text)
        print("\nAccenture ?location=Philippines -> total=", extract_total(r.text),
              "reviews parsed=", len(rs))
        for x in rs:
            print("   ", x.get("jobgroup"), "|", x.get("memberLocation"), "|",
                  x.get("memberLocationCountryIsoCode"), "|", x.get("createdAt"),
                  "| summary:", (x.get("summary") or "")[:50])
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
