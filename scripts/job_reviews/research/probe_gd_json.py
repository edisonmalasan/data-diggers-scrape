"""Find embedded review JSON inside archived Glassdoor HTML."""
import json
import re
import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
URL = ("https://web.archive.org/web/20260731174615id_/"
       "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm")

r = requests.get(URL, headers=H, timeout=120)
t = r.text

# candidate JSON blobs
for name, pat in [
    ("__NEXT_DATA__", r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'),
    ("ld+json", r'<script type="application/ld\+json">(.*?)</script>'),
    ("window._data", r'window\.__[A-Z_]+__\s*=\s*(\{.*?\})\s*;?\s*</script>'),
]:
    ms = re.findall(pat, t, re.S)
    print(f"{name}: {len(ms)} blobs; sizes={[len(m) for m in ms][:5]}")

# any JSON containing review text markers
idx = t.find('"reviewText"')
print("reviewText idx:", idx)
for key in ['"pros"', '"cons"', '"location"', '"jobTitle"', '"rating"', '"reviewDate"', '"authorLocation"', '"title"']:
    print(f"{key}: {t.count(key)}")

# Show context around first '"pros"' occurrence
i = t.find('"pros"')
if i != -1:
    print("\n--- context around first \"pros\" ---")
    print(t[max(0, i - 1500): i + 1500])
