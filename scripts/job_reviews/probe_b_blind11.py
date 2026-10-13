"""Phase 27: Blind — isolate why location filtering fails (bare country value; comma
value on Accenture)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blind_extract import extract_reviews, extract_total  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def main() -> int:
    f = Fetcher("blind")
    tests = [
        ("g_bare_ph", "https://www.teamblind.com/company/Google/reviews?location=Philippines"),
        ("acc_city", "https://www.teamblind.com/company/Accenture/reviews?location=New%20York%2C%20NY"),
        ("g_page2", "https://www.teamblind.com/company/Google/reviews?page=2"),
    ]
    try:
        for name, u in tests:
            r = f.get(u, timeout=30, stream_to=STORAGE / f"blind_{name}.html")
            rs = extract_reviews(r.text)
            locs = sorted({x.get("memberLocation") or "?" for x in rs})
            dates = [x.get("createdAt", "")[:10] for x in rs[:3]]
            print(f"{name}: total={extract_total(r.text)} n={len(rs)} dates={dates} locs={locs[:6]}")
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
