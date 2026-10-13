"""Inspect saved Manila-index HTML for employer links / payload / errors."""
import re
from pathlib import Path

STORAGE = Path(__file__).resolve().parents[1] / ".storage"
t = (STORAGE / "gd6_manila.html").read_text(encoding="utf-8", errors="replace")
print("bytes:", len(t))
print("title:", re.findall(r"<title>([^<]*)</title>", t))
eids = set(re.findall(
    r"/Reviews/([A-Za-z0-9%.\-_ ]{2,60})-Reviews-(?:E|EI_IE)(\d+)", t))
print("employer links:", len(eids))
for s, e in sorted(eids)[:50]:
    print("   ", e, s)
esc = t.replace('\\"', '"')
print("has reviews payload:", '"reviews":[' in esc)
print("sign-in count:", t.lower().count("sign in"))
# any review snippets / locations
for m in re.finditer(r"Makati|Manila|Quezon|Cebu", t):
    print("   loc ctx:", t[max(0, m.start() - 60):m.start() + 60].replace("\n", " "))
    break
