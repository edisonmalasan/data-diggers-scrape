"""CDX probe: learn Glassdoor E-ids for candidate PH-heavy employers.

For each candidate slug, query ALL-time captures of
  www.glassdoor.com/Reviews/<slug>*  (prefix, no date filter, collapse urlkey)
and extract slug -> E-id mappings. Light queries (~1.5s spacing).
Saves hits -> .storage/gd_ph_eids.json
"""
import json
import re
import time
from pathlib import Path

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"
STORAGE = Path(__file__).resolve().parents[1] / ".storage"

# slug prefixes (Glassdoor lowercases/hyphenates): both global BPOs & PH cos
SLUGS = [
    # global BPO / IT employers with big PH workforces
    "teleperformance", "concentrix", "taskus", "alorica", "everise",
    "foundever", "sutherland", "transcom", "sykes", "housecall",
    "microsourcing", "cloudstaff", "asticom", "ihermes", "eastvantage",
    "telus", "modis", "nde", "genpact", "teleperformance",
    # IT/consulting multinationals
    "accenture", "ibm", "cognizant", "infosys", "wipro", "capgemini",
    "deloitte", "ey", "kpmg", "pwc", "sap", "oracle", "cisco", "dxc",
    "ntt", "itsu", "hitachi", "tata-consultancy", "hcltech", "techmahindra",
    # PH companies
    "globe-telecom", "globe", "pldt", "smart-communications", "smart",
    "jollibee", "jollibee-foods", "ayala", "ayala-land", "ayala-corp",
    "bdo", "bdo-unibank", "bank-of-the-philippine", "metrobank",
    "security-bank", "unionbank", "bpi", "eastwest-banking",
    "sm-investments", "sm-prime", "robinsons-land", "megaworld",
    "manila-water", "meralco", "cebu-pacific", "abs-cbn", "gma-network",
    "philippine-airlines", "pal", "voyager-innovations", "gcash", "mynt",
    "maya-network", "paymaya", "insular-life", "sunlife-financial",
    "nestle-philippines", "unilever-philippines", "shell Philippines",
    "pepsico-philippines", "coca-cola-philippines", "grab", "lazada",
    "shopee", "dbs", "standard-chartered", "hsbc",
    "manila-electric", "jgc", "first-gen", "energy-development",
    "bench", "golden-abc", "suyen", "emperador",
]

PAT = re.compile(r"/Reviews/([A-Za-z0-9%.\-_ ]+?)-Reviews-(?:E|EI_IE)(\d+)")

hits: dict[str, dict] = {}
for i, slug in enumerate(SLUGS):
    prefix = f"www.glassdoor.com/Reviews/{slug}"
    params = {"url": prefix, "matchType": "prefix", "showNumPages": "false",
              "filter": ["statuscode:200"], "collapse": "urlkey",
              "fl": "original", "limit": "30"}
    for attempt in range(3):
        try:
            r = requests.get(CDX, params=params, headers=H, timeout=60)
            if r.status_code != 200:
                raise RuntimeError(f"status {r.status_code}")
            for line in r.text.splitlines():
                m = PAT.search(line)
                if m and m.group(2) not in ("1196434",):
                    hits.setdefault(f"{m.group(1).lower()}|{m.group(2)}",
                                    {"slug": m.group(1), "eid": m.group(2),
                                     "prefix": slug})
            break
        except Exception as e:  # noqa: BLE001
            print(f"[{slug}] attempt {attempt}: {e}")
            time.sleep(6)
    print(f"{i + 1}/{len(SLUGS)} {slug}: total hits {len(hits)}")
    time.sleep(1.5)

(STORAGE / "gd_ph_eids.json").write_text(json.dumps(hits, indent=1),
                                         encoding="utf-8")
print("\n== hits ==")
for v in sorted(hits.values(), key=lambda x: x["slug"]):
    print(f"  E{v['eid']}  {v['slug']}  (matched {v['prefix']})")
print("SAVED -> .storage/gd_ph_eids.json")
