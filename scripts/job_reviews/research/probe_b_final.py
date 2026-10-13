"""Phase 16: final evidence checks — wellfound sitemap/paths, blind + layoff deep URLs
via plain HTTP (record status only)."""
from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def wellfound() -> None:
    f = Fetcher("wellfound")
    r = f.get("https://wellfound.com/basics.xml.gz", allow="application/gzip,*/*",
              stream_to=STORAGE / "wellfound_basics.xml.gz")
    raw = r.content
    txt = gzip.decompress(raw).decode("utf-8", "replace") if raw[:2] == b"\x1f\x8b" \
        else raw.decode("utf-8", "replace")
    (STORAGE / "wellfound_basics.xml").write_text(txt, encoding="utf-8")
    urls = re.findall(r"<loc>(.*?)</loc>", txt)
    print("wellfound basics.xml:", r.status_code, "urls:", len(urls))
    for pat in ("review", "/company/", "salaries"):
        hits = [u for u in urls if pat in u.lower()]
        print(f"  '{pat}': {len(hits)}", hits[:3])
    for u in ["https://wellfound.com/", "https://wellfound.com/salaries"]:
        resp = f.get(u, timeout=25)
        m = re.search(r"<title>(.*?)</title>", resp.text, re.S | re.I)
        print("  PATH", u, "->", resp.status_code,
              "| title:", (re.sub(r"\s+", " ", m.group(1)).strip()[:70] if m else "?"))


def blind_deep() -> None:
    f = Fetcher("blind")
    r = f.get("https://www.teamblind.com/company/Google", timeout=25)
    m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
    print("blind /company/Google via HTTP ->", r.status_code,
          "| title:", (re.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else "?"),
          "| err-page:", "Something went wrong" in r.text)


def layoff_deep() -> None:
    f = Fetcher("layoff")
    r = f.get("https://www.thelayoff.com/t/1m2nh0jde", timeout=25)
    m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
    print("layoff /t/ via HTTP ->", r.status_code,
          "| title:", (re.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else "?"))


def main() -> int:
    for fn in (wellfound, blind_deep, layoff_deep):
        try:
            fn()
        except StopSite as e:
            print(fn.__name__, "STOPPED", e)
        except Exception as e:  # noqa: BLE001
            print(fn.__name__, "ERROR", type(e).__name__, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
