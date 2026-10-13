"""Map full review-card DOM inside archived Glassdoor pages (Wayback id_ raw HTML)."""
import re
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
URL = ("https://web.archive.org/web/20260731174615id_/"
       "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm")

r = requests.get(URL, headers=H, timeout=120)
soup = BeautifulSoup(r.text, "lxml")
print("status", r.status_code, "len", len(r.text))

# find label nodes for Pros
labels = [e for e in soup.find_all(string=re.compile(r"^\s*Pros\s*$"))]
print("pros label nodes:", len(labels))

MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}"
if labels:
    lab = labels[0]
    node = lab.parent
    for depth in range(10):
        if node is None:
            break
        txt = node.get_text(" ", strip=True)
        flags = {
            "date": bool(re.search(MONTH, txt)),
            "helpful": "Helpful" in txt,
            "loc_hint": bool(re.search(r"\((?:Philippines|US|United States|England)", txt)),
            "job_hint": bool(re.search(r"Current employee|Former employee|Employed for", txt)),
            "len": len(txt),
        }
        print(f"depth={depth} tag={node.name} cls={str(node.get('class'))[:80]} {flags}")
        if flags["date"] and flags["helpful"] and len(txt) < 6000:
            print("\n=== FULL CARD TEXT ===")
            print(txt[:2500])
            print("\n=== CARD HTML (first 3000) ===")
            print(str(node)[:3000])
            break
        node = node.parent
