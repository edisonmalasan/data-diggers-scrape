"""Phase 3: wellfound / handshake / wttjuk structure via plain HTTP."""
from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def main() -> int:
    # --- wellfound: sitemap -> do review/company URLs exist publicly? ---
    f = Fetcher("wellfound")
    try:
        r = f.get("https://wellfound.com/sitemap.xml.gz", allow="application/gzip,*/*",
                  stream_to=STORAGE / "wellfound_sitemap.xml.gz")
        if r.status_code == 200 and r.content[:2] == b"\x1f\x8b":
            txt = gzip.decompress(r.content).decode("utf-8", "replace")
            (STORAGE / "wellfound_sitemap.xml").write_text(txt, encoding="utf-8")
            urls = re.findall(r"<loc>(.*?)</loc>", txt)
            print("wellfound sitemap urls:", len(urls))
            for pat in ("review", "salary", "salaries", "company"):
                hits = [u for u in urls if pat in u.lower()]
                print(f"  '{pat}': {len(hits)} e.g. {hits[:3]}")
        else:
            print("wellfound sitemap status", r.status_code, r.content[:100])

        # a public company page?
        for u in ["https://wellfound.com/company/stripe",
                  "https://wellfound.com/company/stripe/reviews",
                  "https://wellfound.com/salaries"]:
            resp = f.get(u, stream_to=STORAGE / (re.sub(r"\W+", "_", u).strip("_")[-60:] + ".html"))
            m = re.search(r"<title>(.*?)</title>", resp.text, re.S)
            print("WF", u, "->", resp.status_code,
                  "| title:", (m.group(1).strip()[:90] if m else "?"),
                  "| final:", resp.url)
    except StopSite as e:
        print("wellfound STOPPED", e)

    # --- handshake ---
    f = Fetcher("handshake")
    try:
        r = f.get("https://joinhandshake.com/sitemap.xml", allow="application/xml,text/plain,*/*",
                  stream_to=STORAGE / "handshake_sitemap.xml")
        txt = r.text
        urls = re.findall(r"<loc>(.*?)</loc>", txt)
        print("handshake sitemap urls:", len(urls))
        for pat in ("review", "employer", "feedback", "company"):
            hits = [u for u in urls if pat in u.lower()]
            print(f"  '{pat}': {len(hits)} e.g. {hits[:3]}")
        for u in ["https://joinhandshake.com/employers/",
                  "https://joinhandshake.com/employer-reviews/",
                  "https://app.joinhandshake.com/employers/reviews"]:
            resp = f.head(u)
            print("HS", u, "->", resp.status_code, resp.headers.get("Location", ""))
    except StopSite as e:
        print("handshake STOPPED", e)

    # --- wttj uk ---
    f = Fetcher("wttjuk")
    try:
        r = f.get("https://uk.welcometothejungle.com/", stream_to=STORAGE / "wttjuk_home.html")
        m = re.search(r"<title>(.*?)</title>", r.text, re.S)
        print("WTTJ home", r.status_code, "| title:", (m.group(1).strip()[:100] if m else "?"),
              "| final:", r.url)
        # one employer page (structure check only)
        r2 = f.get("https://uk.welcometothejungle.com/en/companies")
        m2 = re.search(r"<title>(.*?)</title>", r2.text, re.S)
        print("WTTJ companies", r2.status_code, "| title:", (m2.group(1).strip()[:100] if m2 else "?"),
              "| final:", r2.url)
        # does any PH marker appear on homepage?
        for kw in ("Philippines", "Manila", "Remote"):
            print(f"  kw {kw!r} on home:", r.text.count(kw))
    except StopSite as e:
        print("wttj STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
