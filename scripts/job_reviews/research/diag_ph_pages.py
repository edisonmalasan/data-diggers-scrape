"""Diagnostic: re-fetch PH pages that produced items in the resweep and show
the exact per-item gate decision chain (date -> text -> csit -> country ->
location), with raw repr() of the country field."""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from scrape_indeed_wb import extract_items  # noqa: E402
from scrape_jobstreet import CS_IT_EXCLUDE, CS_IT_RE, is_ph_location  # noqa: E402
from scrape_indeed_wb2 import LATEST_FILE, archive_get, polite  # noqa: E402
from scrape_indeed_wb import DATE_OK_RE  # noqa: E402

URLS = [
    "https://ph.indeed.com/cmp/Keyence/reviews",
    "https://ph.indeed.com/cmp/Twist-Resources/reviews",
    "https://ph.indeed.com/cmp/Coherent-Corp.-1/reviews",
    "https://ph.indeed.com/cmp/Yellow-Brick-Road-Productions/reviews",
    "https://ph.indeed.com/cmp/Precepts-Electro--tech-Construction-Corp./reviews",
    "https://ph.indeed.com/cmp/Kaizenaire-Pte.-Ltd./reviews",
]

latest = json.loads(LATEST_FILE.read_text(encoding="utf-8")) \
    if LATEST_FILE.exists() else {}


def txt(v):
    if isinstance(v, dict):
        return (v.get("text") or "").strip()
    if isinstance(v, str):
        return v.strip()
    return ""


for url in URLS:
    ts = latest.get(url)
    if not ts:
        print(f"[skip] no cached ts for {url}")
        continue
    snap = f"https://web.archive.org/web/{ts}id_/{url}"
    r = archive_get(snap, timeout=150)
    polite()
    if r is None or r.status_code != 200:
        print(f"[fail] {url}")
        continue
    items = extract_items(r.text)
    if items is None:
        print(f"[no payload] {url}")
        continue
    print(f"\n=== {url} ({len(items)} items) ===")
    for it in items:
        date = (it.get("submissionDate") or "").strip()
        job = (it.get("jobTitle") or "").strip()
        country = it.get("country", "<MISSING>")
        loc = (it.get("location") or "").strip()
        body = txt(it.get("title")) + txt(it.get("text"))
        pros, cons = txt(it.get("pros")), txt(it.get("cons"))
        if not DATE_OK_RE.match(date):
            gate = "drop_date"
        elif not (body or pros or cons):
            gate = "drop_text"
        elif not (CS_IT_RE.search(job) and not CS_IT_EXCLUDE.search(job)):
            gate = "drop_csit"
        else:
            c = country.strip() if isinstance(country, str) else country
            if isinstance(c, str):
                ok = (c.upper() == "PH") if c else True  # page_is_ph=True here
            else:
                ok = c is None
            gate = "COUNTRY-OK" if ok else f"drop_country({c!r})"
            if ok and not is_ph_location(loc):
                gate += " -> drop_location"
            elif ok:
                gate += " -> ** CANDIDATE ROW **"
        print(f"  {gate:45} | {date:18} | {job[:32]:32} | "
              f"country={country!r:12} | loc={loc[:28]!r}")
    time.sleep(0.5)
