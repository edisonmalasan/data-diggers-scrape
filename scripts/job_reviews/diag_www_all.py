"""Sample www.indeed.com ?fcountry=ALL pages (the only www class that shows
non-US reviews) and tally country values — decisive for whether country='PH'
ever appears on www. Read-only."""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import CS_IT_EXCLUDE, CS_IT_RE, DATE_OK_RE, extract_items  # noqa: E402
from scrape_jobstreet import is_ph_location  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402

INV = STORAGE / "indeed_wb_urls.json"
LATEST = STORAGE / "indeed_wb_latest.json"
DONE = STORAGE / "indeed_wb_done3.json"


def main() -> int:
    inv = json.loads(INV.read_text(encoding="utf-8"))["items"]
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    done = set(json.loads(DONE.read_text(encoding="utf-8")))

    # keep latest ts per url
    allpages: dict[str, str] = {}
    for e in inv:
        if "www.indeed.com" in e["url"] and re.search(r"fcountry=ALL\b", e["url"]):
            u = e["url"]
            if u not in allpages or e["ts"] > allpages[u]:
                allpages[u] = e["ts"]
    print(f"www fcountry=ALL unique pages: {len(allpages)} "
          f"(already done: {sum(u in done for u in allpages)})")

    # prefer already-done (latest cached ts) first? No — sample unfetched too.
    # Take a spread: every Nth page.
    urls = sorted(allpages)
    step = max(1, len(urls) // 16)
    sample = urls[::step][:16]

    c_all: collections.Counter = collections.Counter()
    c_pass: collections.Counter = collections.Counter()
    cand = []
    for n, u in enumerate(sample, 1):
        ts = latest.get(u) or allpages[u]
        r = archive_get(f"https://web.archive.org/web/{ts}id_/{u}",
                        tries=3, timeout=120)
        if r is None or r.status_code != 200:
            print(f"[{n}] FAIL {None if r is None else r.status_code} :: {u[:110]}")
            polite()
            continue
        items = extract_items(r.text) or []
        local = collections.Counter()
        for it in items:
            c = it.get("country")
            c = c.strip() if isinstance(c, str) else ("<missing>" if c is None else repr(c))
            c_all[c] += 1
            local[c] += 1
            text = " ".join(x for x in
                            ((it.get("title") or {}).get("text") if isinstance(it.get("title"), dict)
                             else (it.get("title") or ""),
                             (it.get("text") or {}).get("text") if isinstance(it.get("text"), dict)
                             else (it.get("text") or "")) if x)
            # simpler text check using same fields as build_row
            def _t(v):
                if isinstance(v, dict):
                    return (v.get("text") or "").strip()
                return v.strip() if isinstance(v, str) else ""
            body = "\n".join(x for x in (_t(it.get("title")), _t(it.get("text"))) if x)
            if (DATE_OK_RE.match((it.get("submissionDate") or "").strip()) and
                    (body or _t(it.get("pros")) or _t(it.get("cons"))) and
                    CS_IT_RE.search((it.get("jobTitle") or "")) and
                    not CS_IT_EXCLUDE.search((it.get("jobTitle") or ""))):
                c_pass[c] += 1
                if c.upper() == "PH" or c == "<missing>":
                    cand.append((c, it.get("jobTitle"), it.get("submissionDate"),
                                 it.get("location"), u))
        flag = "  <-- NON-US" if any(k not in ("US",) for k in local) else ""
        print(f"[{n}] items={len(items)} countries={dict(local)}{flag} :: {u[:105]}")
        polite()

    print("\n===== fcountry=ALL sample: ALL items country tally =====")
    print(dict(c_all.most_common()))
    print("===== date+csit+text passers country tally =====")
    print(dict(c_pass.most_common()))
    print(f"PH/missing passers: {len(cand)}")
    for c in cand[:20]:
        print("  CANDIDATE:", c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
