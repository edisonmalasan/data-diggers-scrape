"""Probe round 3: Reddit PH-work subreddits (JSON API) for 2026 review-style posts.

The summative instructions explicitly allow gathering data from different
sources ("ex: social media, blogs, etc."), and r/phcareers + r/buhaycorpo are
the main PH workplace-discussion communities. This probe checks:
  - API reachability (old.reddit/.json) from this machine
  - 2026 post volume, and how many posts name a company + a CS/IT job title
    (the two hard contract fields that can be extracted VERBATIM from posts)
"""
from __future__ import annotations

import json
import re
import time

import requests

H = {"User-Agent": "data-mining-student-research/1.0 (summative activity; "
                   "contact: student group DATA DIGGERS)"}
CSIT = re.compile(
    r"\b(software|programmer|developer|devops|qa|quality assurance|tester|"
    r"data (scientist|analyst|engineer|analytics)|dataSci|machine learning|"
    r"information technology|\bit\b|IT support|help ?desk|service desk|"
    r"systems? (analyst|administrator)|network (engineer|admin)|cyber ?security|"
    r"security analyst|cloud (engineer|architect)|full ?stack|front ?end|back ?end|"
    r"web (developer|dev)|mobile (developer|dev)|android|ios|ui/?ux|business analyst|"
    r"technical support|database|DBA|SAP|Salesforce|software engineer|"
    r"computer engineer|computer science|CS/IT|programmer|application support|"
    r"solutions? architect|infrastructure engineer|site reliability|SRE)\b",
    re.I,
)
COMPANY_HINT = re.compile(
    r"\b(Accenture|Globe|Smart|PLDT|Maya|GCash|UnionBank|BPI|BDO|Metrobank|"
    r"SecurityBank|Cebu Pacific|Jollibee|Shopee|Lazada|Grab|Teleperformance|"
    r"Concentrix|Foundever|Alorica|TaskUs|Telus|iQor|Globant|EPAM|Cognizant|"
    r"Wipro|Infosys|TCS|Capgemini|DXC|IBM|Manulife|AXA|AIA|Insular|"
    r"Multisys|ECC|Neodesign|Norkom|Curotek|Solve|Fitcloud|Coinsph|"
    r"Saladbox|Sprout|Kalibrr|Kata|OneHalf|Cloudstaff|MicroSourcing|"
    r"TeleTech|Alorica|Meridian|VXi|Foundever|TaskUs|Concentrix)\b",
    re.I,
)

for sub in ("phcareers", "buhaycorpo"):
    url = f"https://old.reddit.com/r/{sub}/search.json"
    params = {"q": "2026", "restrict_sr": 1, "sort": "new", "t": "year",
              "limit": 100}
    try:
        r = requests.get(url, params=params, headers=H, timeout=45)
        print(f"r/{sub} search -> {r.status_code} len={len(r.text)}")
        if r.ok:
            data = r.json()
            kids = data.get("data", {}).get("children", [])
            print(f"  posts: {len(kids)}")
            n2026 = n_csit = n_comp = 0
            for k in kids:
                d = k["data"]
                ts = d.get("created_utc", 0)
                y = time.gmtime(ts).tm_year
                txt = f"{d.get('title', '')} {d.get('selftext', '')[:600]}"
                if y == 2026:
                    n2026 += 1
                    if CSIT.search(txt):
                        n_csit += 1
                        if COMPANY_HINT.search(txt):
                            n_comp += 1
            print(f"  2026 posts={n2026} csit={n_csit} csit+company={n_comp}")
            for k in kids[:8]:
                d = k["data"]
                if time.gmtime(d.get("created_utc", 0)).tm_year == 2026:
                    print(f"    [{time.strftime('%Y-%m-%d', time.gmtime(d['created_utc']))}] "
                          f"{d.get('title', '')[:90]}")
    except Exception as e:  # noqa: BLE001
        print(f"r/{sub} ERR {e!r:.150}")
    time.sleep(3)

# new posts listing (no query filter) — measures raw 2026 flow
for sub in ("phcareers", "buhaycorpo"):
    try:
        r = requests.get(f"https://old.reddit.com/r/{sub}/new.json",
                         params={"limit": 100}, headers=H, timeout=45)
        if r.ok:
            kids = r.json().get("data", {}).get("children", [])
            yrs = {}
            for k in kids:
                y = time.gmtime(k["data"].get("created_utc", 0)).tm_year
                yrs[y] = yrs.get(y, 0) + 1
            print(f"r/{sub}/new years: {yrs}")
    except Exception as e:  # noqa: BLE001
        print(f"r/{sub}/new ERR {e!r:.150}")
    time.sleep(3)
print("DONE")
