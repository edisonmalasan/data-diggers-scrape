"""Dump all <article> review cards from archived Glassdoor page."""
import re
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
URL = ("https://web.archive.org/web/20260731174615id_/"
       "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm")

r = requests.get(URL, headers=H, timeout=120)
soup = BeautifulSoup(r.text, "lxml")

arts = soup.find_all("article")
print("articles:", len(arts))
for i, a in enumerate(arts[:6], 1):
    txt = a.get_text(" | ", strip=True)
    print(f"\n--- article {i} ({len(txt)} chars) ---")
    print(txt[:900])
    # children outline
    for ch in a.find_all(recursive=False):
        print("   child:", ch.name, ch.get("class"), "->",
              ch.get_text(" ", strip=True)[:110])

# where is the job title / location? search for patterns
full = r.text
print("\n'out of 5' occurrences:", full.count("out of 5"))
print("'authorLocation' occurrences:", full.count("authorLocation"))
print("'Manila' occurrences:", full.count("Manila"))
print("'Philippines' occurrences:", full.count("Philippines"))
m = re.findall(r"aria-label=\"[^\"]*out of 5[^\"]*\"", full)
print("aria rating labels sample:", m[:5])
# job title markers
for pat in ["Current employee", "Former employee", "Employed for", "recommends", "CEO"]:
    print(f"{pat!r}: {full.count(pat)}")
