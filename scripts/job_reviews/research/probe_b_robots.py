"""Phase 1: robots.txt + homepage reachability for the 6 Site-B targets."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

SITES = [
    ("fishbowl", "https://www.fishbowlapp.com/robots.txt", "https://www.fishbowlapp.com/"),
    ("blind", "https://www.teamblind.com/robots.txt", "https://www.teamblind.com/"),
    ("layoff", "https://www.thelayoff.com/robots.txt", "https://www.thelayoff.com/"),
    ("handshake", "https://www.joinhandshake.com/robots.txt", "https://www.joinhandshake.com/"),
    ("wellfound", "https://wellfound.com/robots.txt", "https://wellfound.com/"),
    ("wttjuk", "https://uk.welcometothejungle.com/robots.txt", "https://uk.welcometothejungle.com/en"),
]


def main() -> int:
    STORAGE.mkdir(parents=True, exist_ok=True)
    for site, robots, home in SITES:
        f = Fetcher(site)
        try:
            r = f.get(robots, allow="text/plain,*/*", stream_to=STORAGE / f"robots_{site}.txt")
            if r.status_code == 200 and "sitemap" in r.text.lower():
                smaps = [ln.strip() for ln in r.text.splitlines()
                         if ln.lower().startswith("sitemap:")]
                (STORAGE / f"sitemaps_{site}.txt").write_text("\n".join(smaps), encoding="utf-8")
            r2 = f.get(home, stream_to=STORAGE / f"home_{site}.html")
            print(f"== {site}: robots={r.status_code} home={r2.status_code} "
                  f"title_snip={r2.text[:0]}")
        except StopSite as e:
            print(f"== {site}: STOPPED {e}")
        except Exception as e:  # noqa: BLE001
            print(f"== {site}: ERROR {type(e).__name__} {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
