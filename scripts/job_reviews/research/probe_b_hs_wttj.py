"""Phase 8: handshake employer-feedback reality check + WTTJ UK employer profile check."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def main() -> int:
    # --- handshake ---
    f = Fetcher("handshake")
    try:
        r = f.get("https://joinhandshake.com/employers/",
                  stream_to=STORAGE / "hs_employers.html")
        txt = r.text
        plain = re.sub(r"<[^>]+>", " ", txt)
        plain = re.sub(r"\s+", " ", plain)
        print("HS /employers/ status:", r.status_code, "| final:", r.url)
        for kw in ("review", "feedback", "rating", "reviews"):
            idxs = [m.start() for m in re.finditer(kw, plain, re.I)][:3]
            for i in idxs:
                print(f"   kw {kw!r}: ...{plain[max(0, i-90):i+110]}...")
        # login wall check on the actual app
        r2 = f.get("https://app.joinhandshake.com/", stream_to=STORAGE / "hs_app.html")
        m = re.search(r"<title>(.*?)</title>", r2.text, re.S | re.I)
        print("HS app status:", r2.status_code, "| final:", r2.url,
              "| title:", (m.group(1).strip()[:80] if m else "?"))
        plain2 = re.sub(r"<[^>]+>", " ", r2.text)
        for kw in ("sign in", "log in", "school", "email"):
            i = plain2.lower().find(kw)
            if i >= 0:
                print(f"   app kw {kw!r}: ...{re.sub(chr(92)+'s+', ' ', plain2[max(0,i-70):i+90])}...")
    except StopSite as e:
        print("handshake STOPPED", e)

    # --- wttj uk: one employer profile ---
    f = Fetcher("wttjuk")
    try:
        home = (STORAGE / "wttjuk_home.html").read_text(encoding="utf-8", errors="replace")
        links = sorted(set(re.findall(r'href="(/en/companies/[^"]+)"', home)))
        print("WTTJ company links:", len(links), links[:5])
        if links:
            u = "https://uk.welcometothejungle.com" + links[0]
            r = f.get(u, stream_to=STORAGE / "wttjuk_employer.html")
            m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
            print("WTTJ employer:", r.status_code, "| final:", r.url,
                  "| title:", (m.group(1).strip()[:90] if m else "?"))
            plain = re.sub(r"<[^>]+>", " ", r.text)
            for kw in ("Philippines", "Manila", "London", "locations", "salary"):
                print(f"   kw {kw!r}:", plain.count(kw))
            # any review/rating content?
            for kw in ("review", "employee rating"):
                print(f"   kw {kw!r}:", len(re.findall(kw, plain, re.I)))
        # does a PH-localised domain exist?
        for dom in ["https://ph.welcometothejungle.com/", "https://www.welcometothejungle.com/en/philippines"]:
            rr = f.head(dom)
            print("HEAD", dom, "->", rr.status_code, rr.headers.get("Location", ""))
    except StopSite as e:
        print("wttj STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
