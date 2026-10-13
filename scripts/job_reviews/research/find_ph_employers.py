"""Which PH-relevant employers already have Glassdoor E-ids in our Wayback set."""
import json
import re
from pathlib import Path

STORAGE = Path(__file__).resolve().parents[1] / ".storage"
rows = json.loads((STORAGE / "glassdoor_urls.json").read_text(encoding="utf-8"))

PAT = re.compile(
    r"/Reviews/([A-Za-z0-9%.\\-_]+?)-Reviews-(?:E|EI_IE)(\d+)", re.I)

PH_NAMES = [
    "accenture", "teleperformance", "concentrix", "telus", "taskus", "alorica",
    "foundever", "sykes", "igenius", "ibm", "deloitte", "ey-", "kpmg",
    "pwc", "sap", "oracle", "cisco", "globe", "pldt", "smart-", "maya-",
    "jollibee", "ayala", "bdo", "bpi", "metrobank", "securitybank",
    "sm-prime", "sm-investments", "robinsons", "megaworld", "mannaland",
    "manila-water", "meralco", "cebu-pacific", "cebupacific", "pal-",
    "abs-cbn", "gma-", "emperador", "jgc", "tata", "infosys", "wipro",
    "cognizant", "capgemini", "shopee", "lazada", "grab", "gcash",
    "mynt", "unionbank", "eastwest", "chinabank", "rcbc", "landbank",
    "douglas", "everise", "alorica", "foundever", "teleperformance",
    "ihermes", "sutherland", "taskus", "foundever", "transcom",
    "microsourcing", "cloudstaff", "asticom", "introhive",
    "insular", "sunlife", "axonize", "first-philippine",
    "voyager", "gcash", "maybank", "securitybank",
    "nestle", "unilever", "p&g", "procter", "shell", "chevron",
    "jti", "pmftc", "philip-morris",
]
PH_TOKEN = re.compile(
    r"philippin|manila|cebu|makati|quezon|davao|pampanga|ilocos|mindanao|"
    r"visayas|luzon|filipin|bpo|bureau-one|ecloud", re.I)

found = {}
for r in rows:
    m = PAT.search(r["url"])
    if not m:
        continue
    slug, eid = m.group(1), m.group(2)
    key = (slug.lower(), eid)
    found.setdefault(key, r["url"])

print(f"total named employer pages: {len(found)}")

hits = []
for (slug, eid), url in found.items():
    if PH_TOKEN.search(slug) or any(n.strip("-") in slug for n in PH_NAMES):
        hits.append((slug, eid))

print(f"PH-relevant matches: {len(hits)}")
for s, e in sorted(set(hits)):
    print(f"  E{e}  {s}")
