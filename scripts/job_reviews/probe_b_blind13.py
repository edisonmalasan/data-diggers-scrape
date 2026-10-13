"""Phase 29: Blind — country filter uses ISO code; test ?location=PH / =IN."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blind_extract import extract_reviews, extract_total  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def main() -> int:
    f = Fetcher("blind")
    tests = [
        ("acc_IN", "https://www.teamblind.com/company/Accenture/reviews?location=IN"),
        ("acc_PH", "https://www.teamblind.com/company/Accenture/reviews?location=PH"),
    ]
    try:
        for name, u in tests:
            r = f.get(u, timeout=30, stream_to=STORAGE / f"blind_{name}.html")
            rs = extract_reviews(r.text)
            tot = extract_total(r.text)
            print(f"{name}: total={tot} n={len(rs)}")
            for x in rs[:8]:
                print("    ", x.get("jobgroup"), "|", x.get("memberLocation"), "|",
                      x.get("memberLocationCountryIsoCode"), "|", x.get("createdAt", "")[:10],
                      "|", (x.get("summary") or "")[:40])
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
