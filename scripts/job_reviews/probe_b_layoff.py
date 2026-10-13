"""Phase 2: thelayoff.com structure — company page, thread links, post metadata."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def main() -> int:
    f = Fetcher("layoff")
    try:
        r = f.get("https://www.thelayoff.com/accenture",
                  stream_to=STORAGE / "layoff_accenture.html")
        html = r.text
        hrefs = sorted(set(re.findall(r'href="(/t/[^"]+|https://www\.thelayoff\.com/t/[^"]+)"', html)))
        print("thread hrefs:", len(hrefs))
        for h in hrefs[:20]:
            print("  ", h)
        # date-like strings
        dates = sorted(set(re.findall(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}\b", html)))
        print("dates found:", dates[:20])
        iso = sorted(set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", html)))
        print("iso dates:", iso[:20])
        # any 2026 mention
        print("2026 count:", html.count("2026"))
        # title
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        print("title:", m.group(1).strip() if m else None)
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
