"""Analyze Indeed inventory query params: fjobtitle / floc / fcountry distribution."""
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_jobstreet import CS_IT_EXCLUDE, CS_IT_RE  # noqa: E402

STORAGE = Path(__file__).resolve().parent / ".storage"
d = json.loads((STORAGE / "indeed_wb_urls.json").read_text(encoding="utf-8"))

fjt = Counter()
floc = Counter()
fcountry = Counter()
with_fjt_csit = {}          # url -> ts  (CS/IT title-filtered pages)
csit_ts = []
n = 0
for e in d["items"]:
    u, ts = e["url"], str(e["ts"])
    n += 1
    q = parse_qs(urlsplit(u).query)
    jt = (q.get("fjobtitle") or [""])[0]
    lo = (q.get("floc") or [""])[0]
    co = (q.get("fcountry") or [""])[0]
    if jt:
        fjt[jt] += 1
    if lo:
        floc[lo] += 1
    if co:
        fcountry[co] += 1
    if jt and CS_IT_RE.search(jt) and not CS_IT_EXCLUDE.search(jt):
        key = (e["host"], urlsplit(u).path, jt)
        if key not in with_fjt_csit or ts > with_fjt_csit[key]:
            with_fjt_csit[key] = ts

print(f"items={n}")
print(f"with fjobtitle={sum(fjt.values())} unique={len(fjt)}")
print(f"with floc={sum(floc.values())} unique={len(floc)}")
print(f"with fcountry={sum(fcountry.values())} values={dict(fcountry)}")
print(f"\nCS/IT fjobtitle-filtered unique pages: {len(with_fjt_csit)}")
print("top fjobtitle values:", fjt.most_common(25))
print("top floc values:", floc.most_common(25))

# company paths covered by CS/IT title filter
paths = Counter(k[1] for k in with_fjt_csit)
print(f"unique company paths with CS/IT fjobtitle: {len(paths)}")
json.dump([{"host": k[0], "path": k[1], "fjobtitle": k[2], "ts": v}
           for k, v in sorted(with_fjt_csit.items(), key=lambda x: -x[1])],
          open(STORAGE / "indeed_csit_pages.json", "w"), indent=0)
print("wrote .storage/indeed_csit_pages.json")
