"""Extract review payloads from live Glassdoor HTML: JSON-LD + RSC + card DOM."""
import html as htmlmod
import json
import re
from pathlib import Path

STORAGE = Path(__file__).resolve().parents[1] / ".storage"
t = (STORAGE / "live4_glassdoor_final.html").read_text(encoding="utf-8",
                                                       errors="replace")

# 1) JSON-LD blocks
for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>',
                     t, re.S):
    raw = htmlmod.unescape(m.group(1))
    try:
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print("ld+json parse fail:", e)
        continue
    if isinstance(data, dict):
        data = [data]
    types = [d.get("@type") for d in data if isinstance(d, dict)]
    print("ld+json block types:", types)
    reviews = [d for d in data if isinstance(d, dict)
               and d.get("@type") == "Review"]
    if reviews:
        print("  review count:", len(reviews))
        print("  keys of first:", sorted(reviews[0].keys()))
        print("  sample:", json.dumps(reviews[0], ensure_ascii=False)[:800])

# 2) card DOM: identity row / detail contexts
for pat in ["review-identity-row", "review-detail",
            "review-rating-label", "ReviewDetail_metrics"]:
    i = t.find(pat)
    print(f"\n--- {pat!r} @ {i} ---")
    if i >= 0:
        print(t[i - 200:i + 700].replace("\n", " ")[:900])

# 3) RSC __next_f payloads: find review-ish JSON fragments
payload = "".join(re.findall(
    r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', t, re.S))
print("\nRSC payload chars:", len(payload))
for key in ["pros", "cons", "jobTitle", "location", "reviewBody",
            "employmentStatus", "degree", "featured", "submitDate"]:
    print(f"  {key}: {payload.count(key)}")

# find a windowed sample around 'cons'
i = payload.find('\\"cons\\"')
if i < 0:
    i = payload.find("cons")
print("\n--- RSC around cons ---")
print(payload[max(0, i - 700):i + 700][:1400])
