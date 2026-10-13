"""Decisive www sampling: (a) individual review PERMALINK pages (tier 6,
27,986 never fetched — one review each, country field per review),
(b) more ?fcountry=ALL pages, (c) CDX probes for legacy PH hosts.
Tallies country values and flags any PH/missing-country candidate.
Read-only; does not touch state/staging.
"""
from __future__ import annotations

import collections
import json
import random
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import (CS_IT_EXCLUDE, CS_IT_RE, DATE_OK_RE, cdx_query,  # noqa: E402
                              extract_items)
from scrape_jobstreet import is_ph_location  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402

INV = STORAGE / "indeed_wb_urls.json"
LATEST = STORAGE / "indeed_wb_latest.json"
DONE = STORAGE / "indeed_wb_done3.json"

PH_HEAVY = re.compile(
    r"accenture|teleperformance|concentrix|cognizant|tcs|capgemini|telus|"
    r"taskus|alorica|iqor|vxi|ibm|genpact|dxc|infosys|wipro|deloitte|kpmg|"
    r"ey|pwc|globant|epam|everise|ibex|51talk|shopee|lazada|grab|foundever|"
    r"sykes|microsourcing|optum|manulife|eclerx|sutherland|transcom",
    re.I)


def _t(v):
    if isinstance(v, dict):
        return (v.get("text") or "").strip()
    if isinstance(v, str):
        return v.strip()
    return ""


def tally(url: str, html: str, c_all: collections.Counter,
          c_pass: collections.Counter, cand: list) -> int:
    items = extract_items(html) or []
    for it in items:
        c = it.get("country")
        c = c.strip() if isinstance(c, str) else ("<missing>" if c is None else repr(c))
        c_all[c] += 1
        text = " ".join(x for x in (_t(it.get("title")), _t(it.get("text"))) if x)
        if (DATE_OK_RE.match((it.get("submissionDate") or "").strip())
                and (text or _t(it.get("pros")) or _t(it.get("cons")))
                and CS_IT_RE.search((it.get("jobTitle") or ""))
                and not CS_IT_EXCLUDE.search((it.get("jobTitle") or ""))):
            c_pass[c] += 1
            if c.upper() == "PH" or c == "<missing>":
                cand.append((c, it.get("jobTitle"), it.get("submissionDate"),
                             it.get("location"), url))
    return len(items)


def fetch(url: str, ts: str) -> str | None:
    r = archive_get(f"https://web.archive.org/web/{ts}id_/{url}",
                    tries=3, timeout=120)
    polite()
    if r is None or r.status_code != 200:
        print(f"   FAIL {None if r is None else r.status_code} :: {url[:100]}")
        return None
    return r.text


def main() -> int:
    inv = json.loads(INV.read_text(encoding="utf-8"))["items"]
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    done = set(json.loads(DONE.read_text(encoding="utf-8")))

    # latest ts per url
    ts_by_url: dict[str, str] = {}
    for e in inv:
        if e["url"] not in ts_by_url or e["ts"] > ts_by_url[e["url"]]:
            ts_by_url[e["url"]] = e["url"] and e["ts"]

    permalinks = [u for u in ts_by_url
                  if "www.indeed.com" in u and "/reviews/review?" in u]
    perm_ph = [u for u in permalinks if PH_HEAVY.search(u)]
    perm_other = [u for u in permalinks if u not in set(perm_ph)]
    # permalinks carrying a country filter?
    perm_fc = [u for u in permalinks if "fcountry=" in u]
    print(f"www permalinks: {len(permalinks)} (PH-heavy slug: {len(perm_ph)}, "
          f"with fcountry param: {len(perm_fc)})")
    for u in perm_fc[:5]:
        print("   fcountry permalink:", u[:120])

    allp = [u for u in ts_by_url
            if "www.indeed.com" in u and re.search(r"fcountry=ALL\b", u)]
    print(f"www fcountry=ALL pages: {len(allp)}")

    c_all: collections.Counter = collections.Counter()
    c_pass: collections.Counter = collections.Counter()
    cand: list = []

    def run_group(name: str, urls: list[str], n: int) -> None:
        print(f"\n===== {name} (sampling {n}) =====")
        random.Random(7).shuffle(urls)
        got = 0
        for u in urls:
            if got >= n:
                break
            ts = latest.get(u) or ts_by_url.get(u)
            if not ts:
                continue
            html = fetch(u, ts)
            if html is None:
                continue
            got += 1
            k = tally(u, html, c_all, c_pass, cand)
            print(f"   [{got}] items={k} :: {u[:110]}")

    run_group("PH-heavy www permalinks", perm_ph, 15)
    run_group("random www permalinks", perm_other, 15)
    run_group("www fcountry=ALL (fresh sample)", allp, 15)

    # ---- CDX probes for legacy / other PH hosts
    print("\n===== CDX probes: legacy PH hosts =====")
    for host in ("indeed.ph", "www.indeed.ph", "ph.indeed.com/cmp/"):
        rows = cdx_query({"url": host, "matchType": "domain" if host.count("/") == 0 else "prefix",
                          "limit": "500"})
        rev = [r for r in rows if "/reviews" in r[0].lower()]
        print(f"   {host}: rows={len(rows)} review-ish={len(rev)}")
        for r in rev[:5]:
            print("      ", r[0][:120], r[1])
        polite()

    print("\n===== country tally: ALL sampled items =====")
    print(dict(c_all.most_common()))
    print("===== date+csit+text passers by country =====")
    print(dict(c_pass.most_common()))
    print(f"PH/missing passers: {len(cand)}")
    for c in cand[:20]:
        print("   CANDIDATE:", c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
