"""Diagnostic 2: re-fetch cached www.indeed.com pages and show the exact
per-item gate decision chain with raw country field values."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from scrape_indeed_wb import DATE_OK_RE, extract_items  # noqa: E402
from scrape_jobstreet import CS_IT_EXCLUDE, CS_IT_RE, is_ph_location  # noqa: E402
from scrape_indeed_wb2 import LATEST_FILE, archive_get, polite  # noqa: E402

URLS = [
    "https://www.indeed.com/cmp/Microsoft/reviews?fjobtitle=Principal+Software+Engineer",
    "https://www.indeed.com/cmp/Infosys/reviews?fjobtitle=Application+Support+Analyst",
    "https://www.indeed.com/cmp/Vxi-Global-Solutions/reviews",
    "https://www.indeed.com/cmp/Concentrix/reviews?ftopic=jobsecadv",
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
    page_is_ph = url.lower().startswith("https://ph.") or "fcountry=ph" in url.lower()
    print(f"\n=== {url} ({len(items)} items, page_is_ph={page_is_ph}) ===")
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
                ok = (c.upper() == "PH") if c else page_is_ph
            else:
                ok = c is None and page_is_ph
            gate = "COUNTRY-OK" if ok else f"drop_country({c!r})"
            if ok:
                gate += " -> drop_location" if not is_ph_location(loc) \
                    else " -> ** CANDIDATE ROW **"
        print(f"  {gate:48} | {date:18} | {job[:30]:30} | "
              f"country={country!r:14} | loc={loc[:30]!r}")
