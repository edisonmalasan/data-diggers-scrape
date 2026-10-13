"""Phase 17: Blind company pages via plain HTTP — inspect ratings/pros/cons/review fields."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def peek(what: str) -> None:
    p = STORAGE / what
    if not p.exists():
        return
    h = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<title>(.*?)</title>", h, re.S | re.I)
    title = re.sub(r"\s+", " ", m.group(1)).strip()[:90] if m else "?"
    print(f"## {what}: len={len(h)} title={title!r}")
    plain = re.sub(r"<script.*?</script>", " ", h, flags=re.S | re.I)
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = re.sub(r"\s+", " ", plain)
    print("   plain[:400]:", plain[:400])
    for kw in ("Pros", "Cons", "Rating", "reviews", "job title", "Location",
               "Philippines", "Manila", "2026"):
        print(f"   kw {kw!r}: {len(re.findall(re.escape(kw), plain, re.I))}")


def main() -> int:
    f = Fetcher("blind")
    urls = {
        "blind_company_google.html": "https://www.teamblind.com/company/Google",
        "blind_company_google_rev.html": "https://www.teamblind.com/company/Google/reviews",
    }
    try:
        for fn, u in urls.items():
            r = f.get(u, timeout=30, stream_to=STORAGE / fn)
            print("saved", fn, r.status_code, r.url)
        peek("blind_company_google.html")
        peek("blind_company_google_rev.html")
    except StopSite as e:
        print("STOPPED", e)
    # also inspect what the basics sitemap of wellfound contains
    p = STORAGE / "wellfound_basics.xml"
    if p.exists():
        urls2 = re.findall(r"<loc>(.*?)</loc>", p.read_text(encoding="utf-8", errors="replace"))
        print("## wellfound basics urls (all):")
        for u in urls2:
            print("   ", u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
