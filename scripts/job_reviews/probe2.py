"""Step 2: enumerate 2026 Wayback snapshots for Glassdoor/Indeed review pages,
and inspect a CareerBliss review page structure."""
import re
import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
CDX = "https://web.archive.org/cdx/search/cdx"


def cdx(name, params, show=10):
    try:
        r = requests.get(CDX, params=params, headers=H, timeout=120)
        lines = [l for l in r.text.splitlines() if l.strip()]
        print(f"== {name}: status={r.status_code} rows={len(lines)}")
        for l in lines[:show]:
            print("   ", l)
        return lines
    except Exception as e:
        print(f"== {name}: ERROR {e}")
        return []


# 1) Glassdoor company review pages captured in 2026 (200s only)
g = cdx("glassdoor-reviews-2026", {
    "url": "www.glassdoor.com/Reviews/", "matchType": "prefix",
    "from": "20260101", "to": "20261008", "filter": ["statuscode:200", "mimetype:text/html"],
    "collapse": "urlkey", "limit": "300", "fl": "original,timestamp"})

# 2) Indeed PH company review pages captured in 2026
i = cdx("indeed-reviews-2026", {
    "url": "ph.indeed.com/cmp/", "matchType": "prefix",
    "from": "20260101", "to": "20261008", "filter": ["statuscode:200"],
    "collapse": "urlkey", "limit": "300", "fl": "original,timestamp"})

# how many of the indeed hits are /reviews pages?
rev = [l for l in i if "/reviews" in l]
print(f"indeed /reviews hits: {len(rev)}")
for l in rev[:20]:
    print("   ", l)

# 3) inspect one archived Glassdoor page for review content
if g:
    url = g[0].split()[0] if len(g[0].split()) == 2 else None
    ts = g[0].split()[1] if len(g[0].split()) == 2 else None
    if url and "Reviews" in url:
        snap = f"https://web.archive.org/web/{ts}id_/{url}"
        r = requests.get(snap, headers=H, timeout=90)
        t = r.text
        print(f"== glassdoor snapshot {url} -> {r.status_code} len={len(t)}")
        dates = sorted(set(re.findall(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, 2026", t)))
        print("   2026 dates:", dates[:12])
        for k in ["Pros", "Cons", "Manila", "Philippines", "reviewText", "authorLocation"]:
            print(f"   {k}: {t.count(k)}")

# 4) CareerBliss structure
r = requests.get("https://www.careerbliss.com/accenture/reviews/", headers=H, timeout=60)
t = r.text
print(f"== careerbliss len={len(t)}")
print("   date patterns:",
      sorted(set(re.findall(r"\d{2}/\d{2}/20\d\d", t)))[:10],
      sorted(set(re.findall(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, 20\d\d", t)))[:10])
print("   Manila count:", t.count("Manila"), "Philippines:", t.count("Philippines"))
m = re.search(r"(Pros.{0,80})", t, re.S)
print("   pros ctx:", (m.group(1)[:120] if m else None))
