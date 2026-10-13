"""Combo analysis: Indeed URLs with PH locations and/or CS/IT job-title filters."""
import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

STORAGE = Path(__file__).resolve().parent / ".storage"
d = json.loads((STORAGE / "indeed_wb_urls.json").read_text(encoding="utf-8"))

PH_LOC = ("manila", "makati", "quezon", "taguig", "pasig", "cebu", "davao",
          "iloilo", "bacolod", "clark", "pampanga", "alabang", "ortigas",
          "mandaluyong", "paranaque", "pasay", "caloocan", "muntinlupa",
          "bulacan", "cavite", "laguna", "batangas", "philippines")
CSIT_JT = ("software", "developer", "programmer", "web ", "mobile", "devops",
           "data ", "database", "sysadmin", "system admin", "network",
           "engineer", "it support", "it helpdesk", "help desk", "technical",
           "quality assurance", "qa ", "coder", "cloud", "security",
           "scientist", "analyst", "architect")

ph_loc_pages = {}      # (host,path) -> ts
csit_pages = {}        # (host,path) -> [(fjobtitle, ts)]
combo = []             # PH loc AND CS/IT title
ph_and_csit_paths = set()
for e in d["items"]:
    u, ts = e["url"], str(e["ts"])
    sp = urlsplit(u)
    q = parse_qs(sp.query)
    lo = (q.get("floc") or [""])[0].lower()
    jt = (q.get("fjobtitle") or [""])[0].lower()
    co = (q.get("fcountry") or [""])[0]
    is_ph_loc = any(p in lo for p in PH_LOC) or co == "PH" or e["host"] == "ph.indeed.com"
    is_csit_jt = bool(jt) and any(t in jt for t in CSIT_JT)
    key = (e["host"], sp.path)
    if is_ph_loc:
        prev = ph_loc_pages.get(key)
        if not ts.startswith("2026"):
            continue
        if not prev or ts > prev:
            ph_loc_pages[key] = ts
    if is_csit_jt:
        csit_pages.setdefault(key, []).append((q.get("fjobtitle", [""])[0], ts))
    if is_ph_loc and is_csit_jt:
        combo.append((e["host"], sp.path, q.get("fjobtitle", [""])[0],
                      q.get("floc", [""])[0], co, ts))
        ph_and_csit_paths.add(sp.path)

print(f"unique PH-located filter pages (2026 captures): {len(ph_loc_pages)}")
print(f"unique CS/IT-title-filtered pages: {len(csit_pages)}")
print(f"COMBO (PH loc AND CS/IT title): {len(combo)} items, "
      f"{len(ph_and_csit_paths)} unique paths")
for c in combo[:30]:
    print("  ", c)
json.dump({"ph_loc": [{"host": k[0], "path": k[1], "ts": v}
                      for k, v in ph_loc_pages.items()],
           "combo": combo},
          open(STORAGE / "indeed_ph_csit.json", "w"), indent=0)
print("wrote .storage/indeed_ph_csit.json")
