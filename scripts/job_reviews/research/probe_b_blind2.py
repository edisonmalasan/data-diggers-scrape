"""Phase 18: parse Blind review cards — extract meta segments (status/loc/title/date)."""
from __future__ import annotations

import html as htm
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE  # noqa: E402

META_RE = re.compile(
    r'<div class="text-xs text-gray-700">(.*?)</div>', re.S)


def segs(html_text: str) -> list[list[str]]:
    out = []
    for m in META_RE.finditer(html_text):
        chunk = m.group(1)
        chunk = re.sub(r"<[^>]+>", "", chunk)
        chunk = htm.unescape(chunk)
        parts = [p.strip() for p in re.split(r"[•·�]+|&#x2022;", chunk) if p.strip()]
        if parts:
            out.append(parts)
    return out


def main() -> int:
    p = STORAGE / "blind_company_google_rev.html"
    h = p.read_text(encoding="utf-8", errors="replace")
    lines = segs(h)
    print("meta lines:", len(lines))
    for s in lines[:15]:
        print("   ", s)
    # segment-position statistics
    for pos in range(4):
        c = Counter(s[pos] for s in lines if len(s) > pos)
        print(f"-- pos{pos} top:", c.most_common(8))
    # any 2026 dates
    dates = [s[-1] for s in lines if s and re.search(r"20\d{2}", s[-1])]
    print("dates:", Counter(dates).most_common(10))
    # PH markers anywhere in review text?
    plain = re.sub(r"<[^>]+>", " ", h)
    for kw in ("Philippines", "Manila", "BGC", "Makati", "Cebu"):
        print(f"kw {kw!r}:", plain.count(kw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
