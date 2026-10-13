"""Decisive www test: fetch the PH-relevant CLASSES still in the queue
(tier 2 CS/IT fjobtitle, tier 3 PH-heavy slugs, tier 4 PH-floc) and tally
country values for every item AND for date+csit+text passers.

Answers: can www.indeed.com ever produce country='PH' (or missing) among
rows that pass the earlier gates?  Read-only w.r.t. sweep state/staging;
logs to .storage/diag_www_passers.log for the final report.
"""
from __future__ import annotations

import collections
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import CS_IT_EXCLUDE, CS_IT_RE, DATE_OK_RE, extract_items  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite  # noqa: E402

QUEUE = STORAGE / "indeed_wb_queue3.json"
LATEST = STORAGE / "indeed_wb_latest.json"
DONE = STORAGE / "indeed_wb_done3.json"
OUT = STORAGE / "diag_www_passers.log"


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
    q = json.loads(QUEUE.read_text(encoding="utf-8"))["items"]
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    done = set(json.loads(DONE.read_text(encoding="utf-8")))

    by_tier: dict[int, list[dict]] = collections.defaultdict(list)
    for e in q:
        if e["url"] not in done:
            by_tier[e["tier"]].append(e)
    print("remaining queue by tier:",
          {t: len(v) for t, v in sorted(by_tier.items())})

    plan: list[dict] = []
    plan += by_tier.get(2, [])                       # all CS/IT fjobtitle
    plan += by_tier.get(4, [])                       # all PH-floc
    heavy = by_tier.get(3, [])
    random.Random(5).shuffle(heavy)
    plan += heavy[:60]                               # sample of PH-heavy

    c_all: collections.Counter = collections.Counter()
    c_pass: collections.Counter = collections.Counter()
    cand = []
    log("=== diag_www_passers: PH-relevant queued www pages ===")

    for n, e in enumerate(plan, 1):
        url = e["url"]
        ts = latest.get(url) or e["ts"]
        r = archive_get(f"https://web.archive.org/web/{ts}id_/{url}",
                        tries=3, timeout=150)
        polite()
        if r is None or r.status_code != 200:
            log(f"[{n}/{len(plan)}] FAIL {None if r is None else r.status_code} :: {url[:110]}")
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
                                 it.get("location"), url))
        flag = "" if set(local) <= {"US"} else "  <-- NON-US"
        log(f"[{n}/{len(plan)}] items={len(items)} passers={n_pass} "
            f"countries={dict(local)}{flag} :: {url[:105]}")

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
