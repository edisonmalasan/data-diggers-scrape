"""Phase 22: Blind — verify filter param names (jobTitle/employeeStatus) and
location value format."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

HEAD_RE = re.compile(r'<h3 class="font-semibold"> &quot;<!-- -->(.*?)<!-- -->&quot;', re.S)
CNT_RE = re.compile(r"Results of <!-- -->\s*([\d,]+)")


def heads(html: str) -> list[str]:
    return [re.sub(r"<[^>]+>", "", x) for x in HEAD_RE.findall(html)]


def main() -> int:
    f = Fetcher("blind")
    base = "https://www.teamblind.com/company/Google/reviews"
    variants = [
        ("jt", base + "?jobTitle=" + "Software%20Engineer"),
        ("es", base + "?employeeStatus=Former%20Employee"),
        ("loc2", base + "?location=Manila%2C%20Philippines"),
        ("loc3", base + "?location=Philippines&jobTitle=Software%20Engineer"),
    ]
    try:
        plain = (STORAGE / "blind_plain.html").read_text(encoding="utf-8", errors="replace")
        pheads = heads(plain)
        for name, u in variants:
            r = f.get(u, timeout=30, stream_to=STORAGE / f"blind_f_{name}.html")
            hs = heads(r.text)
            m = CNT_RE.search(r.text)
            same = hs == pheads
            print(f"{name}: {r.status_code} results={m.group(1) if m else '?'} "
                  f"cards={len(hs)} same_as_plain={same}")
            for t in hs[:2]:
                print("      ", t[:90])
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
