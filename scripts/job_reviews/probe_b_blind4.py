"""Phase 20: Blind — fetch a few JS chunks and grep for review-filter query params."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def main() -> int:
    h = (STORAGE / "blind_company_google_rev.html").read_text(encoding="utf-8", errors="replace")
    srcs = sorted(set(re.findall(r'src="(https://[^"]*teamblind[^"]*\.js|/_next/static/[^"]+\.js)"', h)))
    print("js chunks:", len(srcs))
    for s in srcs[:25]:
        print("   ", s)
    # prefer chunks likely holding review UI (names often hint)
    rank = sorted(srcs, key=lambda s: (0 if re.search(r"review|company", s, re.I) else 1))
    f = Fetcher("blind")
    try:
        for s in rank[:6]:
            url = s if s.startswith("http") else "https://www.teamblind.com" + s
            r = f.get(url, allow="application/javascript,*/*", timeout=30)
            txt = r.text
            hits = set(re.findall(r'[?&](location|locations|jobTitle|job_title|employee|filter)[A-Za-z_]*=', txt))
            hits |= set(re.findall(r'"(location[A-Za-z_]*)"', txt))
            print(f"   chunk {url.split('/')[-1][:60]}: {r.status_code} len={len(txt)} hits={sorted(hits)[:10]}")
            # show snippets around 'reviews?'
            for m in list(re.finditer(r"reviews\?[^\"'\s]{0,80}", txt))[:4]:
                print("      snip:", m.group(0))
            for m in list(re.finditer(r".{60}locationFilter.{60}|.{60}location_filter.{60}", txt))[:4]:
                print("      snip2:", m.group(0).replace("\n", " "))
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
