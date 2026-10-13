"""Step 3a: inspect CareerBliss review page DOM (dates? locations? pagination?)."""
import re
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

url = "https://www.careerbliss.com/accenture/reviews/"
r = requests.get(url, headers=H, timeout=60)
soup = BeautifulSoup(r.text, "lxml")

# candidate review containers
for sel in ["div.bliss-review", "div.review-container", "div[class*=review]", "article"]:
    els = soup.select(sel)
    if els:
        print(f"selector {sel!r}: {len(els)} matches")

# find text that looks like a review and its metadata
blocks = soup.select("div[class*=review]")
print("total review-ish divs:", len(blocks))
for b in blocks[:6]:
    cls = " ".join(b.get("class", []))
    txt = " ".join(b.get_text(" ", strip=True).split())[:300]
    print(f"\n--- class={cls}\n{txt}")

# dates anywhere
dates = sorted(set(re.findall(r"[A-Z][a-z]{2,8} \d{1,2}, 20\d\d", r.text)))
print("\nlong dates:", dates[:20])
dates2 = sorted(set(re.findall(r"\d{1,2}/\d{1,2}/20\d\d", r.text)))
print("slash dates:", dates2[:20])
rel = sorted(set(re.findall(r"\b\d+ (?:day|week|month|year)s? ago\b", r.text)))
print("relative dates:", rel[:10])
print("pagination hints:", [a.get("href") for a in soup.select("a[href*=page]")][:10])
