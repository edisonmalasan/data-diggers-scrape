"""Locate ALL review-like nodes in archived Glassdoor HTML (not just <article>)."""
import re
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
URL = ("https://web.archive.org/web/20260731174615id_/"
       "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm")

r = requests.get(URL, headers=H, timeout=120)
soup = BeautifulSoup(r.text, "lxml")

# every element whose DIRECT text nodes include 'Current/Former employee'
nodes = []
for e in soup.find_all(True):
    direct = " ".join(str(c) for c in e.children if getattr(c, "name", None) is None)
    if re.search(r"(Current|Former) employee", direct):
        nodes.append(e)
print("nodes with direct employment text:", len(nodes))
seen_cls = {}
for e in nodes:
    cls = " ".join(e.get("class") or []) or e.name
    seen_cls[cls] = seen_cls.get(cls, 0) + 1
print("by class/tag:", seen_cls)

# inspect first few: climb to container w/ date
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}"
for e in nodes[:5]:
    node = e
    for d in range(7):
        if node is None:
            break
        txt = node.get_text(" ", strip=True)
        if re.search(MONTH, txt) and "Pros" in txt:
            print(f"\n=== CARD (depth {d}, tag={node.name}, cls={str(node.get('class'))[:70]}) len={len(txt)}")
            print(txt[:800])
            break
        node = node.parent

# how many date+Pros combos overall?
cards = [e for e in soup.find_all(["article", "div", "li"])
         if re.search(MONTH, e.get_text(" ", strip=True)) and "Pros" in e.get_text()
         and len(e.get_text(strip=True)) < 4000]
# keep only smallest (deepest) ones
def is_smaller_parent(c):
    return any(c is x.parent or (x is not c and c in x.parents) for x in cards)
smallest = [c for c in cards if not any(x is not c and c in x.parents for x in cards)]
print("\nsmallest date+Pros containers:", len(smallest))
for c in smallest[:10]:
    print("  -", c.name, str(c.get("class"))[:70], "|", c.get_text(" ", strip=True)[:130])
