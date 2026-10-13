"""Phase 10: document-only exclusions — ONE homepage/HEAD check each, then stop.

For each domain we only confirm the fast-fail reason (wrong country vs
no employee-review content). No scraping.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, Fetcher  # noqa: E402

# (key, url, expected reason to confirm)
DOMAINS = [
    ("seek.com.au", "https://www.seek.com.au/", "AU-only job board: no PH employment"),
    ("stepstone.com", "https://www.stepstone.com/", "DE/EU job board: no PH employment"),
    ("totaljobs.com", "https://www.totaljobs.com/", "UK job board: no PH employment"),
    ("reed.co.uk", "https://www.reed.co.uk/", "UK job board: no PH employment"),
    ("jobthai.com", "https://www.jobthai.com/", "Thai job board: no PH employment"),
    ("simplyhired.com", "https://www.simplyhired.com/", "job aggregator: no employee-review content"),
    ("jooble.org", "https://jooble.org/", "job aggregator: no employee-review content"),
    ("hiring.cafe", "https://hiring.cafe/", "job aggregator: no employee-review content"),
    ("kununu.com", "https://www.kununu.com/", "employee reviews exist but employer base is DACH/EU, no PH employment"),
]


def main() -> int:
    out = []
    for key, url, _why in DOMAINS:
        try:
            f = Fetcher(key.split(".")[0])
            r = f.get(url, timeout=25)
            title = ""
            m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()[:110]
            final = r.url
            ph_hits = len(re.findall(r"philippin|\bmanila\b", r.text, re.I))
            rev_hits = len(re.findall(r"employee review|company reviews|employer reviews", r.text, re.I))
            line = (f"{key}: HTTP {r.status_code} final={final} title={title!r} "
                    f"PH_kw={ph_hits} review_kw={rev_hits}")
            print(line, flush=True)
            out.append(line)
        except Exception as e:  # noqa: BLE001
            line = f"{key}: ERROR {type(e).__name__} {e}"
            print(line, flush=True)
            out.append(line)
    (STORAGE / "siteb_doconly_checks.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
