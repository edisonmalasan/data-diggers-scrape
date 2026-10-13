"""Final decisive test: refetch a random sample of ALREADY-DONE www list
pages (the class that produced the 111 drop_country passers in run 3) and
tally country values for date+csit+text PASSERS. Read-only; logs to
.storage/diag_done_passers.log.
"""
from __future__ import annotations

import collections
import json
import random
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import CS_IT_EXCLUDE, CS_IT_RE, DATE_OK_RE, extract_items  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402

DONE = STORAGE / "indeed_wb_done3.json"
LATEST = STORAGE / "indeed_wb_latest.json"
INV = STORAGE / "indeed_wb_urls.json"
OUT = STORAGE / "diag_done_passers.log"


def log(msg: str) -> None:
    print(msg, flush=True)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def _t(v):
    if isinstance(v, dict):
        return (v.get("text") or "").strip()
    if isinstance(v, str):
        return v.strip()
    return ""


def main() -> int:
    done = json.loads(DONE.read_text(encoding="utf-8"))
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    inv = json.loads(INV.read_text(encoding="utf-8"))["items"]
    ts_by_url = {}
    for e in inv:
        if e["url"] not in ts_by_url or e["ts"] > ts_by_url[e["url"]]:
            ts_by_url[e["url"]] = e["ts"]

    # www LIST pages only (the run-3 item source), not detail permalinks
    www_list = [u for u in done if "www.indeed.com" in u
                and "/reviews" in urlsplit(u).path
                and not re.search(r"/reviews/[^/?]+", urlsplit(u).path)]
    print(f"done www list pages: {len(www_list)}")
    random.Random(21).shuffle(www_list)
    sample = www_list[:60]

    c_all: collections.Counter = collections.Counter()
    c_pass: collections.Counter = collections.Counter()
    cand = []
    log("=== diag_done_passers: refetched done www list pages ===")
    for n, u in enumerate(sample, 1):
        ts = latest.get(u) or ts_by_url.get(u)
        if not ts:
            continue
        r = archive_get(f"https://web.archive.org/web/{ts}id_/{u}",
                        tries=3, timeout=150)
        polite()
        if r is None or r.status_code != 200:
            log(f"[{n}/{len(sample)}] FAIL {None if r is None else r.status_code} :: {u[:110]}")
            continue
        items = extract_items(r.text) or []
        local: collections.Counter = collections.Counter()
        n_pass = 0
        for it in items:
            c = it.get("country")
            c = c.strip() if isinstance(c, str) else ("<missing>" if c is None else repr(c))
            c_all[c] += 1
            local[c] += 1
            text = " ".join(x for x in (_t(it.get("title")), _t(it.get("text"))) if x)
            if (DATE_OK_RE.match((it.get("submissionDate") or "").strip())
                    and (text or _t(it.get("pros")) or _t(it.get("cons")))
                    and CS_IT_RE.search((it.get("jobTitle") or ""))
                    and not CS_IT_EXCLUDE.search((it.get("jobTitle") or ""))):
                c_pass[c] += 1
                n_pass += 1
                if c.upper() == "PH" or c == "<missing>":
                    cand.append((c, it.get("jobTitle"), it.get("submissionDate"),
                                 it.get("location"), u))
        flag = "" if set(local) <= {"US"} else "  <-- NON-US"
        log(f"[{n}/{len(sample)}] items={len(items)} passers={n_pass} "
            f"countries={dict(local)}{flag} :: {u[:105]}")

    log("\n=== ALL items by country ===")
    log(str(dict(c_all.most_common())))
    log("=== date+csit+text PASSERS by country ===")
    log(str(dict(c_pass.most_common())))
    log(f"PH/missing passers: {len(cand)}")
    for c in cand[:30]:
        log(f"   CANDIDATE: {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
