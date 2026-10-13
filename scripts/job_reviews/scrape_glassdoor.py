"""Scrape Glassdoor PH-relevant reviews from Wayback Machine 2026 snapshots -> CSV.

Why Wayback: glassdoor.com hard-blocks automated live access ("Humans only"),
while web.archive.org is a public archive that permits automated access — the
snapshots are verbatim captures of real Glassdoor review pages from 2026
(DATA_CONTRACT rule 9: we collect only what the archive serves; no bypassing).

Each archived page server-renders a few review cards; we parse rating, date,
headline, job title, employment status, location, pros, cons — then keep only
2026 + CS/IT title + PH location rows (contract section 3).

Run:  python scripts/job_reviews/scrape_glassdoor.py [--target 900] [--limit 700]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scrape_jobstreet import (  # shared contract gates + append (no playwright needed)
    CS_IT_EXCLUDE, CS_IT_RE, PH_RE, TOP_EMPLOYERS, append_rows, count_csv,
    is_ph_location, make_id,
)

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"
URLS_FILE = STORAGE / "glassdoor_urls.json"
DONE_FILE = STORAGE / "glassdoor_done.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
}
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}"
DATE_RE = re.compile(MONTH)
EMP_RE = re.compile(r"(?<!\w)(Current|Former|Anonymous)\s+(?:employee|contractor|intern)\b", re.I)
WIDGET_LINES = {"Recommend", "CEO approval", "Business Outlook", "Helpful", "Show more",
                "Report", "Pros", "Cons", "Flag", "Share", "Read less", "Read more",
                "Yes", "No", "Thumbs up", "Thumbs down"}
ORG_RE = re.compile(r'"@type":\s*"Organization"[^}]*"name":\s*"([^"]+)"')

PH_URL_HIT = re.compile(
    r"Manila|Philippines|philippine|Cebu|Makati|Taguig|Quezon|Pasig|Davao|Iloilo|"
    r"Bacolod|Cagayan|Zamboanga|Baguio|Pampanga|Bulacan|Cavite|Laguna|Batangas|IM995",
    re.I,
)
GD_COMPANY_HIT = re.compile(
    r"/Reviews/(Accenture|IBM|Infosys|Cognizant|DXC|Wipro|TCS|Capgemini|NTT|TechMahindra|"
    r"HCL|LTIMindtree|Mphasis|Globe|PLDT|Smart|UnionBank|BPI|BDO|Metrobank|SecurityBank|"
    r"JP-Morgan|JPMorgan|Citi|Capital-One|Manulife|AXA|Sun-Life|AIA|MetLife|Genpact|Optum|"
    r"Concentrix|Teleperformance|TaskUs|Alorica|TeleTech|Convergys|Sykes|Foundever|iQor|"
    r"Shell|Nestle|Unilever|Procter|Deloitte|PwC|EY|KPMG|Accenture|Microsourcing|"
    r"Emerson|Schneider|Siemens|Honeywell|Collins|Cardinal|Ingram|Fujitsu|Samsung|Dyson)",
    re.I,
)


def load_done() -> set[str]:
    return set(json.loads(DONE_FILE.read_text(encoding="utf-8"))) if DONE_FILE.exists() else set()


def save_done(done: set[str]) -> None:
    DONE_FILE.write_text(json.dumps(sorted(done), indent=0), encoding="utf-8")


# PH-heavy employers whose Glassdoor pages contain PH reviewer cards.
# TOP_EMPLOYERS (anchored prefix match) + extra BPO/tech/pharma PH ops.
PH_EMPLOYER_RE = re.compile(
    TOP_EMPLOYERS.pattern.lstrip("^")
    + r"|concentrix|teleperformance|taskus|everise|ibex|vxi|telus|sykes|foundever|"
    r"iqor|alorica|foundever|maya|mynt|gcash|lazada|grab|foodpanda|247-ai|"
    r"amonix|amdocs|carelon|optum|everest|purolator|lexmark|amon[a-z]*|"
    r"jpmorgan|bpi|bdo|metrobank|securitybank|eastwest|rcbc|china-bank|landbank|"
    r"psbank|maynilad|manila-water|ayala|jollibee|sm-supermalls|bpi",
    re.I,
)


def company_seg(url: str) -> str:
    m = re.search(r"/Reviews/([^/?]+)", url)
    return m.group(1) if m else ""


def rank(item: dict) -> int:
    u = item["url"]
    if "jobTitle" in u:   # Glassdoor's own job-title filter (often tech titles)
        return 0
    if PH_URL_HIT.search(u):
        return 1          # PH cities in path/query OR PH company name
    seg = company_seg(u)
    if PH_EMPLOYER_RE.match(seg):
        return 2          # known big employers with PH workforce
    if GD_COMPANY_HIT.search(u):
        return 3          # global tech/BPO employers (some PH reviewers)
    return 4              # everything else — last resort sweep


def climb_container(lab, max_hops: int = 9):
    """From a 'Pros' label, climb to the review card containing date + status."""
    node = lab
    for _ in range(max_hops):
        if node is None:
            return None
        t = node.get_text(" ", strip=True)
        if DATE_RE.search(t) and EMP_RE.search(t.replace("employee", "employee")) and len(t) < 5000:
            if any(re.search(MONTH, ln) for ln in t.split("\n")) or DATE_RE.search(t):
                return node
        node = node.parent
    return None


def parse_card(cont, page_url: str, company_hint: str, now: str) -> dict | None:
    txt = cont.get_text("\n", strip=True)
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    if len(lines) < 3:
        return None
    # rating + date
    rating = ""
    if re.fullmatch(r"\d(?:\.\d)?", lines[0]):
        rating = lines[0]
    di = next((i for i, l in enumerate(lines) if DATE_RE.fullmatch(l)), None)
    if di is None:
        return None
    review_date = lines[di]
    if "2026" not in review_date:
        return None
    if rating == "" and di > 0 and re.fullmatch(r"\d(?:\.\d)?", lines[di - 1]):
        rating = lines[di - 1]

    # employment status
    ei = next((i for i in range(di + 1, len(lines)) if EMP_RE.match(lines[i])), None)
    emp_status = "Unknown"
    if ei is not None:
        emp_status = "Current" if lines[ei].lower().startswith("current") else (
            "Former" if lines[ei].lower().startswith("former") else "Unknown")

    # headline + job title: lines strictly between date and employment
    body = lines[di + 1: ei if ei is not None else len(lines)]
    body = [b for b in body if b not in WIDGET_LINES]
    job_title = headline = ""
    if ei is None:
        # no employment line: content until 'Pros'
        pr = next((i for i, l in enumerate(body) if l == "Pros"), None)
        body = body[:pr] if pr is not None else body
        if not body:
            return None
        job_title = body[-1]
        headline = " ".join(body[:-1])
    elif len(body) >= 2:
        headline = " ".join(body[:-1])
        job_title = body[-1]
    elif body:
        job_title = body[0]

    # location: line right after employment (unless it's a widget label)
    location = ""
    if ei is not None and ei + 1 < len(lines):
        cand = lines[ei + 1]
        if cand not in WIDGET_LINES and cand != job_title and cand != headline:
            location = cand

    # pros / cons
    def between(start_lbl: str, end_lbls: tuple) -> str:
        try:
            s = lines.index(start_lbl, di)
        except ValueError:
            return ""
        out = []
        for l in lines[s + 1:]:
            if l in end_lbls:
                break
            out.append(l)
        return " ".join(out).strip()

    pros = between("Pros", ("Cons", "Show more", "Helpful"))
    cons = between("Cons", ("Show more", "Helpful", "Recommend", "Flag"))

    review_text = headline
    if not (review_text or pros or cons):
        return None
    if not job_title or not (CS_IT_RE.search(job_title) and not CS_IT_EXCLUDE.search(job_title)):
        return None
    if not is_ph_location(location):
        return None
    company = company_hint or "Unknown"
    return {
        "review_id": make_id(company, job_title, review_date, review_text or pros, page_url),
        "company_name": company,
        "job_title": job_title,
        "department": "",
        "seniority_level": "",
        "employment_status": emp_status,
        "review_date": review_date,
        "rating": rating,
        "review_text": review_text,
        "pros": pros,
        "cons": cons,
        "location": location,
        "source_platform": "glassdoor",
        "source_url": page_url,
        "scraped_at": now,
    }


def company_from_html(soup: BeautifulSoup, orig_url: str, html: str) -> str:
    m = ORG_RE.search(html)
    if m:
        return m.group(1)
    m = re.search(r"/Reviews/([^/]+?)(?:-Reviews|-Manila|_P\d|\.htm|\?|/)", orig_url)
    if m:
        slug = m.group(1)
        slug = re.sub(r"-EI?_?IE?\d+.*$", "", slug)
        slug = re.sub(r"-\d+,\d+.*$", "", slug)
        return slug.replace("-", " ").strip() or "Unknown"
    return "Unknown"


def extract_cards(soup: BeautifulSoup) -> list:
    labels = [e for e in soup.find_all(["p", "span", "div", "h4"])
              if e.get_text(strip=True) == "Pros"]
    cards, seen = [], set()
    for lab in labels:
        cont = climb_container(lab)
        if cont is None or id(cont) in seen:
            continue
        seen.add(id(cont))
        cards.append(cont)
    return cards


def fetch(url: str, timeout: int = 60) -> str | None:
    """HTML, '' for definitive 404/410/403, None for transient failure."""
    for attempt in range(5):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"    429 rate-limited; sleeping {wait}s")
                time.sleep(wait)
                continue
            if r.status_code in (404, 410, 403):
                return ""
            time.sleep(10)
        except requests.RequestException as e:
            wait = min(60, 5 * (2 ** attempt))   # 5,10,20,40,60
            print(f"    fetch error (retry in {wait}s): {type(e).__name__}")
            time.sleep(wait)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=900,
                    help="stop when TOTAL csv rows reach this")
    ap.add_argument("--limit", type=int, default=700, help="max snapshots this run")
    ap.add_argument("--sleep", type=float, default=1.3)
    args = ap.parse_args()

    items = json.loads(URLS_FILE.read_text(encoding="utf-8"))
    done = load_done()
    # best-ranked first; newest capture within a rank (deeper into 2026)
    todo = sorted((i for i in items if i["url"] not in done),
                  key=lambda i: (rank(i), -int(i["ts"])))
    todo = todo[: args.limit]
    print(f"glassdoor urls={len(items)} done={len(done)} todo={len(todo)} "
          f"rows_now={count_csv()} target={args.target}")

    now_iso = lambda: datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    stats = {"ok": 0, "empty": 0, "cards": 0, "kept": 0}

    for n, item in enumerate(todo, 1):
        if count_csv() + len(rows) >= args.target:
            print(f"target {args.target} reached")
            break
        orig, ts = item["url"], item["ts"]
        snap = f"https://web.archive.org/web/{ts}id_/{orig}"
        mark_done = False
        try:
            html = fetch(snap)
            if html is None:
                stats["empty"] += 1          # transient — retry next run
            elif html == "":
                stats["empty"] += 1          # definitive miss
                mark_done = True
            else:
                mark_done = True
                soup = BeautifulSoup(html, "lxml")
                company = company_from_html(soup, orig, html)
                cards = extract_cards(soup)
                stats["cards"] += len(cards)
                kept = 0
                for c in cards:
                    row = parse_card(c, f"https://web.archive.org/web/{ts}/{orig}",
                                     company, now_iso())
                    if row:
                        rows.append(row)
                        kept += 1
                        stats["kept"] += 1
                stats["ok"] += 1
                if n % 20 == 0 or kept:
                    print(f"[{n}/{len(todo)}] {company[:30]}: cards={len(cards)} kept={kept} "
                          f"(new={len(rows)})")
        except KeyboardInterrupt:
            break
        except Exception as e:  # noqa: BLE001
            print(f"[{n}/{len(todo)}] ERROR {orig[:80]}: {type(e).__name__} {e}")
        finally:
            if mark_done:
                done.add(orig)
                save_done(done)
            time.sleep(args.sleep + random.uniform(0, 0.5))

    added, skipped = append_rows(rows)
    print(f"DONE ok={stats['ok']} cards={stats['cards']} kept={stats['kept']} "
          f"-> added={added} deduped={skipped} rows_now={count_csv()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
