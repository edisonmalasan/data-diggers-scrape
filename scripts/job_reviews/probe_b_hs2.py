"""Phase 11: handshake sitemap-0 (any public review URLs?) + jobthai title evidence."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, Fetcher  # noqa: E402


def main() -> int:
    f = Fetcher("handshake")
    r = f.get("https://joinhandshake.com/sitemap-0.xml", allow="application/xml,*/*",
              stream_to=STORAGE / "handshake_sitemap0.xml")
    urls = re.findall(r"<loc>(.*?)</loc>", r.text)
    print("handshake sitemap-0:", r.status_code, "urls:", len(urls))
    for pat in ("review", "feedback", "rating", "employer"):
        hits = [u for u in urls if pat in u.lower()]
        print(f"  '{pat}': {len(hits)}", hits[:4])

    f2 = Fetcher("jobthai")
    r2 = f2.get("https://www.jobthai.com/", timeout=25)
    m = re.search(r"<title>(.*?)</title>", r2.text, re.S | re.I)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else "?"
    print("jobthai:", r2.status_code, "title(utf8-safe):", title.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
