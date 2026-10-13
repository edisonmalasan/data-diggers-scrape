"""Phase 23: Blind — does ?location=<exact facet key> filter server-side?"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

HEAD_RE = re.compile(r'<h3 class="font-semibold"> &quot;<!-- -->(.*?)<!-- -->&quot;', re.S)
CNT_RE = re.compile(r'"total":(\d+)')


def heads(html: str) -> list[str]:
    return [re.sub(r"<[^>]+>", "", x) for x in HEAD_RE.findall(html)]


def main() -> int:
    f = Fetcher("blind")
    base = "https://www.teamblind.com/company/Google/reviews"
    plain = (STORAGE / "blind_plain.html").read_text(encoding="utf-8", errors="replace")
    pheads = heads(plain)
    variants = [
        ("city", base + "?location=" + "New%20York%2C%20NY"),
        ("country", base + "?locationCountry=Philippines"),
        ("iso", base + "?location=PH"),
        ("sortloc", base + "?sort=recent&location=Philippines"),
    ]
    try:
        for name, u in variants:
            r = f.get(u, timeout=30, stream_to=STORAGE / f"blind_g_{name}.html")
            hs = heads(r.text)
            m = CNT_RE.search(r.text.replace('\\"', '"'))
            print(f"{name}: total={m.group(1) if m else '?'} cards={len(hs)} same={hs == pheads}")
            # count PH markers in embedded json
            un = r.text.replace('\\"', '"')
            ph = un.count('"PH"') + len(re.findall(r'"memberLocation":"[^"]*Philippin', un))
            print(f"    ph_markers={ph}")
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
