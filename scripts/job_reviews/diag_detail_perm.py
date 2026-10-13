"""Sample www review-DETAIL permalinks (tier 6, never fetched): does any
carry country='PH'? Focus on PH-heavy employer slugs first, then a random
control. Read-only."""
from __future__ import annotations

import collections
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import (CS_IT_EXCLUDE, CS_IT_RE, DATE_OK_RE,  # noqa: E402
                              extract_items)
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402

INV = STORAGE / "indeed_wb_urls.json"
LATEST = STORAGE / "indeed_wb_latest.json"

PH = re.compile(
    r"accenture|teleperformance|concentrix|cognizant|taskus|alorica|iqor|"
    r"vxi|ibm|genpact|shopee|lazada|grab|globant|epam|everise|ibex|51talk|"
    r"microsourcing|sykes|foundever|optum|manulife|eclerx|sutherland|pldt|"
    r"globe|jollibee|unionbank|bdo|bpi|ayala|sm-|petron", re.I)


def _t(v):
    if isinstance(v, dict):
        return (v.get("text") or "").strip()
    if isinstance(v, str):
        return v.strip()
    return ""


def main() -> int:
    inv = json.loads(INV.read_text(encoding="utf-8"))["items"]
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    ts_by_url: dict[str, str] = {}
    for e in inv:
        if e["url"] not in ts_by_url or e["ts"] > ts_by_url[e["url"]]:
            ts_by_url[e["url"]] = e["ts"]

    detail = [u for u in ts_by_url
              if "www.indeed.com" in u and re.search(r"/reviews/[^/?]+\?id=", u)]
    ph = [u for u in detail if PH.search(u)]
    print(f"www detail permalinks={len(detail)} PH-heavy-slug={len(ph)}")

    c_all: collections.Counter = collections.Counter()
    c_pass: collections.Counter = collections.Counter()
    cand = []

    def sample(name, urls, n):
        print(f"\n===== {name} (n={n}) =====")
        random.Random(11).shuffle(urls)
        got = 0
        for u in urls:
            if got >= n:
                break
            ts = latest.get(u) or ts_by_url[u]
            r = archive_get(f"https://web.archive.org/web/{ts}id_/{u}",
                            tries=3, timeout=120)
            polite()
            if r is None or r.status_code != 200:
                print(f"   FAIL {None if r is None else r.status_code} :: {u[:100]}")
                continue
            got += 1
            items = extract_items(r.text) or []
            loc = collections.Counter()
            for it in items:
                c = it.get("country")
                c = c.strip() if isinstance(c, str) else ("<missing>" if c is None else repr(c))
                c_all[c] += 1
                loc[c] += 1
                text = " ".join(x for x in (_t(it.get("title")), _t(it.get("text"))) if x)
                if (DATE_OK_RE.match((it.get("submissionDate") or "").strip())
                        and (text or _t(it.get("pros")) or _t(it.get("cons")))
                        and CS_IT_RE.search((it.get("jobTitle") or ""))
                        and not CS_IT_EXCLUDE.search((it.get("jobTitle") or ""))):
                    c_pass[c] += 1
                    if c.upper() == "PH" or c == "<missing>":
                        cand.append((c, it.get("jobTitle"), it.get("submissionDate"),
                                     it.get("location"), u))
            print(f"   [{got}] items={len(items)} countries={dict(loc)} :: {u[:105]}")

    sample("PH-heavy detail permalinks", ph, 30)
    sample("random detail permalinks", [u for u in detail if u not in set(ph)], 20)

    print("\n===== ALL sampled items by country =====")
    print(dict(c_all.most_common()))
    print("===== date+csit+text passers by country =====")
    print(dict(c_pass.most_common()))
    print(f"PH/missing passers: {len(cand)}")
    for c in cand[:20]:
        print("   CANDIDATE:", c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
