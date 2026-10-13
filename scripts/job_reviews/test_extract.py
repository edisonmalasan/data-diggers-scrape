"""One-page sanity test of enum_directory.EXTRACT before the full walk."""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
src = (Path(__file__).resolve().parent / "enum_directory.py").read_text(encoding="utf-8")
m = re.search(r'EXTRACT = r"""(.*?)"""', src, re.S)
assert m, "EXTRACT not found"
extract = m.group(1)
print("using EXTRACT (first 200):", extract[:200].replace("\n", " "))

URL = "https://ph.jobstreet.com/companies/directory/information-technology-services"
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()
    pg.goto(URL, timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    pg.mouse.wheel(0, 6000)
    pg.wait_for_timeout(1200)
    cards = pg.evaluate(extract)
    nrev = sum(1 for c in cards if c["rev"])
    print(f"cards={len(cards)} with_reviews={nrev}")
    for c in cards[:5]:
        print(" ", c)
    b.close()
