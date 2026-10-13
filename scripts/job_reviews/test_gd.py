"""Unit-test scrape_glassdoor parsing on one known snapshot."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_glassdoor import extract_cards, parse_card, company_from_html, fetch  # noqa: E402

from bs4 import BeautifulSoup  # noqa: E402

SNAP = ("https://web.archive.org/web/20260731174615id_/"
        "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm")
ORIG = "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm"
TS = "20260731174615"

html = fetch(SNAP)
print("fetched:", bool(html), len(html or ""))
soup = BeautifulSoup(html, "lxml")
company = company_from_html(soup, ORIG, html)
print("company:", company)
cards = extract_cards(soup)
print("cards:", len(cards))
for i, c in enumerate(cards, 1):
    row = parse_card(c, f"https://web.archive.org/web/{TS}/{ORIG}", company, "2026-10-08T00:00:00")
    print(f"\n--- card {i} -> {'KEPT' if row else 'rejected'}")
    if row:
        for k, v in row.items():
            print(f"   {k}: {str(v)[:160]}")
    else:
        # show why: print first 10 lines
        lines = [l for l in c.get_text("\n", strip=True).split("\n") if l.strip()]
        print("   lines:", lines[:12])
