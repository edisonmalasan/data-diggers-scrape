"""Phase 19: Blind reviews — discover server-side filter params (location)."""
from __future__ import annotations

import html as htm
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

META_RE = re.compile(r'<div class="text-xs text-gray-700">(.*?)</div>', re.S)
CNT_RE = re.compile(r'Results of <!-- -->\s*([\d,]+)')


def summarize(h: str) -> tuple[str, list[list[str]], int]:
    m = CNT_RE.search(h)
    count = m.group(1) if m else "?"
    metas = []
    for mm in META_RE.finditer(h):
        chunk = htm.unescape(re.sub(r"<[^>]+>", "", mm.group(1)))
        parts = [p.strip() for p in re.split(r"[•·]+", chunk) if p.strip()]
        metas.append(parts)
    ph = sum(1 for p in metas for seg in p if re.search(r"philippin|manila|cebu|makati", seg, re.I))
    return count, metas, ph


def main() -> int:
    f = Fetcher("blind")
    base = "https://www.teamblind.com/company/Google/reviews"
    variants = [
        ("plain", base + "?page=1"),
        ("location", base + "?location=Philippines&page=1"),
        ("locations", base + "?locations=Philippines&page=1"),
        ("location_kw", base + "?locationKeyword=Philippines&page=1"),
    ]
    try:
        for name, u in variants:
            r = f.get(u, timeout=30, stream_to=STORAGE / f"blind_{name}.html")
            count, metas, ph = summarize(r.text)
            print(f"{name}: {r.status_code} results={count} cards={len(metas)} ph_meta={ph}")
            for s in metas[:3]:
                print("     ", s)
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
