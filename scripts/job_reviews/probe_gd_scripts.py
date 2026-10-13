"""Dump script payloads that contain employment markers in archived Glassdoor HTML."""
import re
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
URL = ("https://web.archive.org/web/20260731174615id_/"
       "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm")

r = requests.get(URL, headers=H, timeout=120)
soup = BeautifulSoup(r.text, "lxml")

hits = []
for s in soup.find_all("script"):
    txt = s.string or ""
    if re.search(r"(Current|Former) employee", txt):
        hits.append((s.get("id"), s.get("type"), len(txt), txt))
print("script hits:", len(hits))
for i, (sid, styp, ln, txt) in enumerate(hits):
    print(f"\n=== script {i}: id={sid} type={styp} len={ln}")
    # locate employment marker context
    m = re.search(r".{600}(?:Current|Former) employee.{600}", txt, re.S)
    if m:
        print(m.group(0)[:1400])
