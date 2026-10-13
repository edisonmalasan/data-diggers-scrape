"""Offline analysis of the saved inventory: find high-yield URL classes
(fcountry=PH, floc PH-city, fjobtitle CS/IT terms, PH-heavy company pages)
and count what's left after the done list. Also check relatedReviews size
in a saved permalink dump. No network.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from scrape_jobstreet import CS_IT_EXCLUDE, CS_IT_RE, PH_RE  # noqa: E402

STORAGE = HERE / ".storage"
inv = json.loads((STORAGE / "indeed_wb_urls.json").read_text(encoding="utf-8"))["items"]
done = set(json.loads((STORAGE / "indeed_wb_done.json").read_text(encoding="utf-8")))
todo = [it for it in inv if it["url"] not in done]
print(f"inventory={len(inv)} done={len(done)} todo={len(todo)}")

FLOC_PH = re.compile(
    r"floc=(Manila|Makati|Taguig|Quezon|Pasig|Cebu|Davao|Clark|Alabang|"
    r"Ortigas|BGC|Bonifacio|Pampanga|Laguna|Cavite|Bulacan|Iloilo|Bacolod|"
    r"Antipolo|Dasmar|Para|Calamba|Santa+Rosa|Baguio|Pampanga)", re.I)


def cls(u: str) -> str:
    low = u.lower()
    if "fcountry=ph" in low:
        return "fcountry_PH"
    if FLOC_PH.search(low):
        return "floc_PH"
    m = re.search(r"fjobtitle=([^&]+)", low)
    if m:
        from urllib.parse import unquote_plus
        title = unquote_plus(m.group(1))
        if CS_IT_RE.search(title) and not CS_IT_EXCLUDE.search(title):
            return "fjobtitle_CSIT"
        return "fjobtitle_other"
    if "ftopic=" in low:
        return "ftopic"
    if "fromjk=" in low or "jt=" in low:
        return "job_ad"
    if re.search(r"/reviews?/[^/]+", low):
        return "permalink"
    return "plain_list"


from collections import Counter  # noqa: E402

c_all, c_todo = Counter(), Counter()
for it in inv:
    c_all[cls(it["url"])] += 1
for it in todo:
    c_todo[cls(it["url"])] += 1
print(f"{'class':16} {'inv':>6} {'todo':>6}")
for k in sorted(c_all, key=lambda x: -c_all[x]):
    print(f"{k:16} {c_all[k]:>6} {c_todo.get(k, 0):>6}")

print("\n-- todo fcountry_PH / floc_PH / fjobtitle_CSIT samples --")
for it in todo:
    k = cls(it["url"])
    if k in ("fcountry_PH", "floc_PH", "fjobtitle_CSIT"):
        print(f"  [{k}] {it['url'][:130]}")

# host split of plain_list todo
hl = Counter(("ph" if "ph.indeed.com" in it["url"] else "www")
             for it in todo if cls(it["url"]) == "plain_list")
print("\nplain_list todo by host:", dict(hl))

# permalink dump relatedReviews size
D = Path(r"C:\Users\Edison\AppData\Local\Temp\opencode")
f = D / "indep_yellowbrick_perma1.html"
if f.exists():
    import json as _json
    t = f.read_text(encoding="utf-8")
    m = re.search(r'<script[^>]*id="comp-initialData"[^>]*>(.*?)</script>', t, re.S)
    data = _json.loads(m.group(1))
    rel = data["individualReviews"].get("relatedReviews") or []
    print("relatedReviews on permalink page:", len(rel))
