"""Probe Kalibrr (PH-native job platform) for employee-review corpus viability.

Kalibrr (kalibrr.com) is Filipino-founded and PH-heavy; robots.txt only
disallows /root and /candidate/profile, so company review pages are
crawl-permitted (DATA_CONTRACT rule 9).

Checks, per company review URL:
  - server-rendered or __NEXT_DATA__ payload availability (no JS needed?)
  - which contract fields are present: job title, employment status,
    review/pros/cons text, date (esp. 2026), rating, location
"""
from __future__ import annotations

import json
import re
import sys

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}


def get(url: str) -> requests.Response:
    r = requests.get(url, headers=H, timeout=45)
    print(f"GET {url} -> {r.status_code} len={len(r.text)}")
    return r


# 1. robots + sitemap hints
get("https://www.kalibrr.com/robots.txt")

# 2. company directory / search page: how are company profile URLs shaped?
r = get("https://www.kalibrr.com/home/companies")
if r.ok:
    for pat in [r'href="(/home/company/[^"#]+)"', r'href="(https://www\.kalibrr\.com/home/company/[^"#]+)"',
                r'"company_id"\s*:\s*(\d+)', r'"slug"\s*:\s*"([^"]+)"']:
        m = sorted(set(re.findall(pat, r.text)))
        print(f"  pattern {pat[:40]!r}: {len(m)} hits; sample={m[:5]}")

# 3. known PH IT/CS-heavy employers — try slug guesses on company profile
CANDS = [
    "accenture", "accenture-in-the-philippines", "ibm", "globant",
    "cognizant", "globe-telecom", "smart-communications", "unionbank",
]
for slug in CANDS:
    u = f"https://www.kalibrr.com/home/company/{slug}"
    try:
        rr = requests.get(u, headers=H, timeout=30, allow_redirects=True)
        tag = "OK" if rr.ok else str(rr.status_code)
        has_rev = "review" in rr.text.lower()
        print(f"  /home/company/{slug}: {tag} len={len(rr.text)} mentions_review={has_rev} final={rr.url[:90]}")
    except Exception as e:  # noqa: BLE001
        print(f"  /home/company/{slug}: ERR {e!r}")

# 4. any Next.js data payload on a company page?
for slug in ["accenture", "ibm"]:
    u = f"https://www.kalibrr.com/home/company/{slug}"
    rr = requests.get(u, headers=H, timeout=30)
    if rr.ok:
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', rr.text, re.S)
        print(f"  NEXT_DATA on {slug}: {'yes len=' + str(len(m.group(1))) if m else 'no'}")
        # any embedded JSON review markers
        for key in ["review", "rating", "pros", "cons", "job_title", "jobTitle"]:
            print(f"    {key!r} count={rr.text.lower().count(key.lower())}")
        sys.exit(0)
