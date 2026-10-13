"""Size the Wayback inventories: hosts, 2026 captures, remaining todo."""
import json
from collections import Counter
from pathlib import Path

STORAGE = Path(__file__).resolve().parent / ".storage"


def load(name):
    return json.loads((STORAGE / name).read_text(encoding="utf-8"))


d = load("indeed_wb_urls.json")
print("indeed_wb_urls.json keys:", {k: (len(v) if hasattr(v, "__len__") else v)
                                    for k, v in d.items()})
for k, v in d.items():
    if isinstance(v, dict):
        print(f"  {k}: subkeys", {kk: len(vv) for kk, vv in list(v.items())[:5]})
        break

# flatten any structure to a list of {url, ts, host} dicts
entries = []
for k, v in d.items():
    if isinstance(v, list):
        entries.extend(v)
    elif isinstance(v, dict):
        for kk, vv in v.items():
            if isinstance(vv, list):
                entries.extend(vv)
print("total entries:", len(entries))
print("sample:", entries[:2])

from urllib.parse import urlsplit  # noqa: E402

hosts = Counter()
years = Counter()
base_pages = set()
for e in entries:
    if isinstance(e, dict):
        u, ts = e.get("url", ""), str(e.get("ts", ""))
    elif isinstance(e, (list, tuple)):
        u, ts = e[0], str(e[1]) if len(e) > 1 else ""
    else:
        u, ts = str(e), ""
    sp = urlsplit(u)
    hosts[sp.netloc] += 1
    years[ts[:4]] += 1
    base_pages.add(f"{sp.scheme}://{sp.netloc}{sp.path}")
    if "fcountry=PH" in u or "fcountry=ph" in u:
        base_pages.add(f"PHFILTER {sp.netloc}{sp.path}")
print("hosts:", dict(hosts))
print("capture years:", dict(sorted(years.items())))
by_host_base = Counter(b.split("/", 3)[2] for b in base_pages if not b.startswith("PHFILTER"))
print("unique base review pages by host:", dict(by_host_base))
print("fcountry=PH unique pages:", sum(1 for b in base_pages if b.startswith("PHFILTER")))

gd = load("glassdoor_done.json")
print("glassdoor done entries:", len(gd))
