"""Parse the RSC reviews array from saved Glassdoor HTML: count, keys, dates."""
import json
import re
from pathlib import Path

STORAGE = Path(__file__).resolve().parent / ".storage"
t = (STORAGE / "live4_glassdoor_final.html").read_text(encoding="utf-8",
                                                       errors="replace")

payload = "".join(re.findall(
    r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', t, re.S))
# unescape JS string (\" -> ", \\ -> \)
payload = payload.replace('\\"', '"').replace("\\\\", "\\")

i = payload.find('"reviews":[')
print("reviews array @", i)
if i >= 0:
    start = payload.index("[", i)
    dec = json.JSONDecoder()
    arr, end = dec.raw_decode(payload[start:])
    print("reviews in array:", len(arr))
    if arr:
        print("keys:", sorted(arr[0].keys()))
        print()
        print(json.dumps(arr[0], ensure_ascii=False, indent=1)[:1500])
        # location + jobTitle + date distribution
        for r in arr[:12]:
            loc = (r.get("location") or {}).get("name")
            jt = (r.get("jobTitle") or {}).get("text")
            print(f"  rating={r.get('rating')} loc={loc!r} "
                  f"job={jt!r} keys_with_date="
                  f"{[k for k in r if 'ate' in k.lower() or 'time' in k.lower()]}")

# how do dates appear per card in DOM? map review_id -> date from HTML
ids = re.findall(r'review_id=(\d+)', t)
dates = re.findall(r'Timestamp_reviewDate__DWohN">([^<]+)<', t)
print("\ndom review_ids:", ids[:15], "count:", len(set(ids)))
print("dom dates:", dates)

# find filter.defaultLocation known URL
import json as j  # noqa: E402
rows = j.loads((STORAGE / "glassdoor_urls.json").read_text(encoding="utf-8"))
for r in rows:
    if "filter." in r["url"]:
        print("\nfilter URL example:", r["url"])
