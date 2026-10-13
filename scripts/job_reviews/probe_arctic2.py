"""Probe round 7: Arctic Shift pagination + gate funnel for r/phcareers 2026.

Fixes probe_arctic.py: sort=created_utc&order=desc, paginate via the
`before` param using the oldest seen created_utc, and verify the 2026
window actually holds. Then applies the SHARED contract gates (CS_IT_RE /
CS_IT_EXCLUDE / PH_RE from scrape_jobstreet.py) against title+selftext to
estimate the keep-yield before writing the real scraper.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scrape_jobstreet import CS_IT_EXCLUDE, CS_IT_RE, PH_RE  # noqa: E402

H = {"User-Agent": "data-mining-student-research/1.0 (summative activity)"}
BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
AFTER = 1767196800    # 2026-01-01 UTC
BEFORE = 1791561600   # 2026-10-10 UTC

COMPANY_RE = re.compile(
    r"\b(Accenture|Globe|Smart|PLDT|Maya|GCash|UnionBank|Union Bank|BPI|BDO|"
    r"Metrobank|Security Bank|Cebu Pacific|Jollibee|Shopee|Lazada|Grab|"
    r"Teleperformance|Concentrix|Foundever|Alorica|TaskUs|Task Us|Telus|TELUS|"
    r"iQor|IQOR|Globant|EPAM|Cognizant|Wipro|Infosys|TCS|Capgemini|DXC|IBM|"
    r"Manulife|AXA|AIA|Insular|Multisys|ECC|Curotek|Coinsph|Coin.ph|Sprout|"
    r"Kalibrr|Kata|Cloudstaff|MicroSourcing|Microsourcing|TeleTech|Meridian|"
    r"VXi|Infor|Oracle|SAP|Microsoft|Google|Amazon|Apple|Accenture|"
    r"Philippine Veterans Bank|PSBank|Robinsons Bank|EastWest|"
    r"ePLDT|Vitro|Converge|DITO|Sky|PLDT Home|MyBusiness|"
    r"51Talk|TaskUs|Foundever|Alorica|iQor|EbixCash|Foundever|"
    r"WNS|Teleperformance|Concentrix|Capgemini|Tech Mahindra|Mphasis|"
    r"HCL|LTIMindtree|Zoho|Trend Micro|Fortinet|Cisco|Dell|HP|"
    r"Accenture|Globe Labs|Ayala|SM (Group|Retail|Malls)|Jollibee|"
    r"Golden ABC|Bench|Puregold|San Miguel|Absolute|Empire East|Megaworld|"
    r"Filinvest|SM Prime|BPI|Bank of the Philippine Islands)\b",
    re.I,
)


def fetch(sub: str, before: int | None = None, limit: int = 100):
    params = {"subreddit": sub, "after": AFTER, "before": before or BEFORE,
              "limit": limit, "sort": "desc"}
    for attempt in range(4):
        try:
            r = requests.get(BASE, params=params, headers=H, timeout=90)
            if r.status_code == 200:
                return r.json().get("data", [])
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            print(f"  http {r.status_code}: {r.text[:120]}")
            return []
        except Exception as e:  # noqa: BLE001
            print(f"  attempt {attempt}: {e!r:.120}")
            time.sleep(8)
    return []


all_posts: list[dict] = []
for sub in ("phcareers", "buhaycorpo"):
    before = None
    seen = 0
    while True:
        batch = fetch(sub, before)
        if not batch:
            break
        all_posts.extend(batch)
        seen += len(batch)
        oldest = min(p["created_utc"] for p in batch)
        yr = time.gmtime(oldest).tm_year
        print(f"  r/{sub}: fetched={seen} oldest={time.strftime('%Y-%m-%d', time.gmtime(oldest))} (year {yr})")
        if yr < 2026 or len(batch) < 10:
            break
        before = int(oldest)
        time.sleep(2)
        if seen >= 12000:
            break

print(f"\nTOTAL 2026 posts fetched: {len(all_posts)}")

# gate funnel on title+selftext
kept = 0
funnel = {"no_csit": 0, "csit_excluded": 0, "no_company": 0,
          "no_ph": 0, "no_text": 0, "kept": 0}
samples = []
for p in all_posts:
    title = p.get("title") or ""
    body = (p.get("selftext") or "")[:4000]
    txt = f"{title}\n{body}"
    if len(txt.strip()) < 120:
        funnel["no_text"] += 1
        continue
    if not CS_IT_RE.search(title):
        funnel["no_csit"] += 1
        continue
    if CS_IT_EXCLUDE.search(title):
        funnel["csit_excluded"] += 1
        continue
    if not COMPANY_RE.search(title):
        funnel["no_company"] += 1
        continue
    if not PH_RE.search(txt):
        funnel["no_ph"] += 1
        continue
    funnel["kept"] += 1
    kept += 1
    if len(samples) < 12:
        d = time.strftime("%Y-%m-%d", time.gmtime(p["created_utc"]))
        samples.append((d, p.get("subreddit"), title[:95]))

print("funnel:", funnel)
print("\nsample kept posts:")
for s in samples:
    print(f"  [{s[0]}] r/{s[1]} :: {s[2]}")

# variant: require CS/IT anywhere in title OR first 300 chars of body
kept2 = 0
for p in all_posts:
    title = p.get("title") or ""
    body = (p.get("selftext") or "")[:400]
    if not CS_IT_RE.search(f"{title} {body}"):
        continue
    if CS_IT_EXCLUDE.search(title):
        continue
    if not COMPANY_RE.search(f"{title} {body}"):
        continue
    if not PH_RE.search(f"{title} {body}"):
        continue
    kept2 += 1
print(f"\nrelaxed (csit/company anywhere in title+first400): kept={kept2}")
print("DONE")
