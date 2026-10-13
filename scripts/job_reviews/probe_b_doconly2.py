# -*- coding: utf-8 -*-
"""Document-only checks: seek.com.au, stepstone.com, totaljobs.com, jobthai.com (1 req each)."""
import os, re, requests

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".storage")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
sites = [
    ("seek_com_au", "https://www.seek.com.au/"),
    ("stepstone_de", "https://www.stepstone.de/"),
    ("totaljobs_uk", "https://www.totaljobs.com/"),
    ("jobthai_th", "https://www.jobthai.com/"),
]
for name, url in sites:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
        body = r.text.lower()
        blob = r.url.lower() + " " + body[:60000]
        print(name, r.status_code, r.url)
        for tag, pat in (("PH mentions", r"philippin|manila|\bcebu\b"), ("EU/UK/AU/TH mentions", r"\baustralia\b|\bdeutschland\b|\bgermany\b|\bunited kingdom\b|\buk\b|\bthailand\b|ภาษาไทย")):
            hits = re.findall(pat, blob)
            print("   ", tag, len(hits))
        open(os.path.join(OUT, "doconly_%s.html" % name), "w", encoding="utf-8").write(r.text[:200000])
    except Exception as e:
        print(name, "ERR", repr(e)[:90])
