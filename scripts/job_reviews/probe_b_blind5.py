"""Phase 21: Blind — fetch ALL js chunks referenced by the reviews page, grep for
filter/search-param logic."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

OUT = STORAGE / "blind_chunks"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    h = (STORAGE / "blind_company_google_rev.html").read_text(encoding="utf-8", errors="replace")
    srcs = sorted(set(re.findall(r'src="(/_next/static/[^"]+\.js)"', h)))
    print("chunks:", len(srcs))
    f = Fetcher("blind")
    try:
        for s in srcs:
            r = f.get("https://www.teamblind.com" + s, allow="application/javascript,*/*", timeout=30)
            if r.status_code != 200:
                continue
            (OUT / s.rsplit("/", 1)[-1]).write_text(r.text, encoding="utf-8", errors="replace")
    except StopSite as e:
        print("STOPPED", e)

    # grep pass
    pats = {
        "reviews_query": re.compile(r"reviews\?[^\"'`\s]{1,90}"),
        "loc_param": re.compile(r"[?&]?(location|locations|loc|city|country)[A-Za-z_]*=(?!=)"),
        "filter_keys": re.compile(r"(?:jobTitle|employeeType|reviewFilter|filterBy|searchParams)"),
        "algolia": re.compile(r"algolia|app_id|searchKey|indexName", re.I),
        "api_path": re.compile(r"\"(/[a-z0-9_\-/]*(?:review|filter|search)[a-z0-9_\-/]*)\"", re.I),
    }
    for p in sorted(OUT.glob("*.js")):
        txt = p.read_text(encoding="utf-8", errors="replace")
        found = {}
        for k, rx in pats.items():
            ms = list(rx.finditer(txt))
            if ms:
                found[k] = [m.group(0)[:110] for m in ms[:3]]
        if found:
            print(f"## {p.name}")
            for k, v in found.items():
                for s in v:
                    print(f"   {k}: {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
