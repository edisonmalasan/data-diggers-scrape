"""Inspect live Glassdoor HTML: locate review cards, fields, embedded payload."""
import json
import re
from pathlib import Path

STORAGE = Path(__file__).resolve().parents[1] / ".storage"
t = (STORAGE / "live4_glassdoor_final.html").read_text(encoding="utf-8",
                                                       errors="replace")

print("bytes:", len(t))
print('data-test="ReviewCard":', t.count('data-test="ReviewCard"'))
print("ReviewCard (raw):", t.count("ReviewCard"))

for pat in [r'data-test="[^"]*"', r'class="[^"]*[Rr]eview[^"]*"']:
    hits = re.findall(pat, t)
    c = {}
    for h in hits:
        c[h] = c.get(h, 0) + 1
    top = sorted(c.items(), key=lambda x: -x[1])[:15]
    print(f"\npattern {pat!r} top hits:")
    for k, v in top:
        print(f"   {v:4d}  {k[:110]}")

# context around a jobTitle occurrence
i = t.find("jobTitle")
print("\n--- jobTitle context ---")
print(t[i - 400:i + 600].replace("\n", " ")[:1000])

# context around "Reviewed" variants
for pat in ["Reviewed", "Current Employee", "Former Employee",
            "Pros:", "Cons:"]:
    j = t.find(pat)
    print(f"\n--- {pat!r} @ {j} ---")
    if j >= 0:
        print(t[j - 150:j + 350].replace("\n", " ")[:500])

# how many reviews embedded: look for recurring marker
m = re.findall(r"data-test=\"ReviewCard\"", t)
print("\nReviewCard data-test count:", len(m))

# RSC / next payload
print("self.__next_f:", t.count("self.__next_f"))
print("__NEXT_DATA__:", t.count("__NEXT_DATA__"))

# date hits with context
dates = list(re.finditer(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d\d", t))
print("\ndate hits:", len(dates))
for d in dates[:6]:
    s = max(0, d.start() - 120)
    print("   ...", t[s:d.end() + 40].replace("\n", " ")[-200:])
