"""Scrape JobStreet PH company reviews -> data/staging_jobstreet.csv (contract schema).

Access notes (DATA_CONTRACT rule 9):
- ph.jobstreet.com sits behind Cloudflare; a real Chrome via Playwright loads it
  normally (no challenge solving, no bypass tricks).
- robots.txt: clean /companies/<slug>/reviews paths are allowed; ANY URL with a
  query string ('Disallow: *?') is disallowed -> we never use ?page=.. etc.
  (~30 most-recent reviews are rendered on page 1 anyway.)
- Reviews are sorted most recent first, so fresh pages are rich in 2026 rows.

Filters (contract section 3): review_date in 2026, CS/IT job_title, PH location,
>=1 of review_text/pros/cons, never fabricated (all fields copied verbatim).

Run:  python scripts/job_reviews/scrape_jobstreet.py [--target 600] [--limit 400]
Resume is automatic (.storage/jobstreet_done.json).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA_CSV = ROOT / "data" / "staging_jobstreet.csv"  # staged; merge_staging folds it into raw
STORAGE = HERE / ".storage"
SLUGS_FILE = STORAGE / "jobstreet_slugs.json"
DONE_FILE = STORAGE / "jobstreet_done.json"

COLUMNS = [
    "review_id", "company_name", "job_title", "department",
    "seniority_level", "employment_status", "review_date", "rating",
    "review_text", "pros", "cons", "location",
    "source_platform", "source_url", "scraped_at",
]

# ---- CS/IT gate (word-boundary aware; group convention from collect.py) ----
# Positive: title must contain a CS/IT phrase. Bare 'engineer'/'developer-in-name'
# is NOT enough (Mechanical/Civil engineers are not CS/IT) — needs a CS/IT qualifier.
CS_IT_RE = re.compile(
    r"\b("
    r"software|programmer|programming|coding|developer|webdev|"
    r"front-?end|back-?end|full-?stack|"
    r"data scientist|data analyst|data engineer|data analytics|analytics|"
    r"machine learning|deep learning|artificial intelligence|\bai\b|nlp|"
    r"information technology|\bit\b|"
    r"systems? analyst|systems? administrator|systems? programmer|"
    r"network engineer|network administrator|network analyst|network specialist|computer operator|"
    r"cyber ?security|information security|security analyst|security engineer|penetration tester|"
    r"devops|site reliability|\bsre\b|cloud engineer|cloud architect|aws|azure|gcp|"
    r"\bqa\b|quality assurance|tester|test engineer|automation tester|"
    r"database|\bdba\b|\bsql\b|"
    r"ui/?ux|ux designer|product analyst|business analyst|"
    r"technical support|help ?desk|service desk|desktop support|application support|support analyst|"
    r"solutions architect|solution architect|technical architect|infrastructure|"
    r"(software|computer|system|network|it|platform|security|validation|quality|telecom) engineer|"
    r"sap |oracle |salesforce|blockchain|game developer|robotics"
    r")(?=\s|$|,|/|-|and\b|,)",
    re.I,
)
# Hard rejects: unmistakably non-CS/IT professions (checked against the title).
# (Bare 'engineer'/'architect' need no exclusion — CS_IT_RE only matches
# CS-qualified forms like 'software engineer', so 'Mechanical Engineer' fails
# the positive gate on its own.)
CS_IT_EXCLUDE = re.compile(
    r"mechanical|electrical|civil|chemical|industrial|mechatronic|"
    r"production|manufacturing|maintenance|quality control inspector|"
    r"nurse|accountant|cashier|driver|waiter|cook|security guard|"
    r"marketing|sales|account executive|customer service|call center|"
    r"\bhr\b|human resource|recruiter|finance|payroll|legal|administrative|"
    r"supply chain|warehouse|logistics|purchasing|procurement|teacher",
    re.I,
)

# ---- PH gate (location must name a PH place/region) ----
PH_RE = re.compile(
    r"philippines|metro manila|manila|makati|taguig|quezon city|pasig|mandaluyong|"
    r"pasay|paranaque|marikina|caloocan|las piñas|las pinas|muntinlupa|valenzuela|"
    r"san juan|pateros|cebu|davao|iloilo|bacolod|cagayan de oro|zamboanga|baguio|"
    r"(?<!los )angeles|pampanga|bulacan|cavite|laguna|batangas|rizal|tarlac|nueva ecija|zambales|"
    r"pangasinan|benguet|ilocos|la union|pampanga|clark|subic|alabang|ortigas|bonifacio|"
    r"bgc|northgate|filinvest|up technohub|iloilo|bacolod|dumaguete|iloilo|"
    r"calabarzon|central luzon|central visayas|western visayas|davao region|"
    r"caraga|region \w+|mindanao|visayas|luzon|bicol|pampanga|ilocos|cagayan|"
    r"zamboanga peninsula|northern mindanao|soccsksargen|barmm|bangsamoro|"
    r"philippine|naga|bacolod|butuan|tacurong|general santos|tagum|digos|"
    r"olongapo|sta\.? rosa|lipa|batangas city|iloilo city|cebu city|davao city",
    re.I,
)

# Defense-in-depth: explicit US/foreign location markers. Guards against PH_RE
# false positives (e.g. "Los Angeles, CA" matching the "angeles" token).
NON_PH_LOC_RE = re.compile(
    r",\s*(A[LKSZEP]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CHJMV]|O[KR]|"
    r"P[AR]|RI|S[CD]|T[NX]|UT|V[TFA]|W[AVY])\.?\s*$"
    r"|\bunited states\b|\busa\b|\bcalifornia\b|los angeles|new york|"
    r"\bsingapore\b|\bindia\b|\bmalaysia\b|\bindonesia\b|\bvietnam\b|\bthailand\b",
    re.I,
)


def is_ph_location(loc: str | None) -> bool:
    """True only when the location names a PH place and not a foreign one."""
    if not loc:
        return False
    return bool(PH_RE.search(loc)) and not NON_PH_LOC_RE.search(loc)


DATE_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+20\d{2}\b")
TENURE_RE = re.compile(
    r"(?:Less than \d+ year|\d+ to \d+ years|More than \d+ years|\d+ year) in the role,\s*"
    r"(current|former) employee",
    re.I,
)

# Tech/BPO/banking-suggesting slug names (secondary priority).
PRIORITY_RE = re.compile(
    r"tech|digital|software|systems|computer|electronic|telecom|network|data|"
    r"cloud|cyber|outsourcing|bpo|solutions|consulting|labs|innov|global|"
    r"bank|health|aerospace|semicon|micro|robot|auto",
    re.I,
)
TOP_EMPLOYERS = re.compile(
    r"^(accenture|ibm|globe-telecom|pldt|unionbank|bank-of-the-philippine-islands|bdo-unibank|"
    r"china-bank|citibank|citigroup|capital-one|jp-morgan|manulife|axa|sun-life|aia|"
    r"philippine-national-bank|meralco|ingram-micro|wipro|infosys|cognizant|dxc-technology|"
    r"capgemini|genpact|optum|concentrix|foundever|alorica|ibex|vxi|51talk|eclerx|"
    r"cardinal-health|collins-aerospace|samsung|fujitsu|denso-ten|dyson|schneider|emerson|"
    r"microsourcing|ayala|shopee|sm-supermalls|jollibee|universal-robina|the-medical-city|"
    r"teleperformance|taskus|telus|sykes|everise|globant|epam|tata|tcs|ntt|hitachi|"
    r"canon|ricoh|oracle|microsoft|google|amazon|adobe|autodesk|salesforce|cisco|dell|hp|"
    r"hewlett|intel|qualcomm|nxp|texas-instruments|analog-devices|microchip|marvell|"
    r"securitybank|metrobank|eastwest|landbank|rcbc|dynaquest|queenband|foundever)",
    re.I,
)

# JS: extract review containers from a JobStreet /reviews page
JS_PARSE = r"""() => {
  const lines0 = s => (s || '').split('\n').map(x => x.trim()).filter(Boolean);
  const labels = [...document.querySelectorAll('span,div')].filter(
    e => (e.innerText || '').trim() === 'The good things');
  const out = [];
  const seen = new Set();
  for (const lab of labels) {
    let node = lab, cont = null;
    for (let i = 0; i < 10 && node; i++) {
      const t = node.innerText || '';
      if (/Helpful/.test(t) &&
          /\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+20\d\d\b/.test(t)) {
        cont = node; break;
      }
      node = node.parentElement;
    }
    if (!cont || seen.has(cont)) continue;
    seen.add(cont);
    const ratingEl = cont.querySelector('[aria-label*="out of 5"]');
    const aria = ratingEl ? (ratingEl.getAttribute('aria-label') || '') : '';
    const m = aria.match(/([\d.]+)\s*out of/);
    out.push({
      rating: m ? m[1] : '',
      text: cont.innerText || '',
      lines: lines0(cont.innerText),
    });
  }
  const company = (document.title.match(/Reviews\s+(.+?)\s+employee ratings/) ||
                   document.title.match(/^About\s+(.+?)\s+Company/) ||
                   [null, ''])[1].trim();
  return {company, reviews: out};
}"""


def make_id(company: str, title: str, date: str, text: str, url: str) -> str:
    raw = "|".join([company, title, date, text[:120], url]).encode("utf-8")
    return "rv_" + hashlib.sha1(raw).hexdigest()[:12]


def parse_review(raw: dict, company: str, url: str, now: str) -> dict | None:
    lines = raw["lines"]
    text = raw["text"]
    if not lines:
        return None
    # 1) date line
    idx_date = next((i for i, l in enumerate(lines) if DATE_RE.fullmatch(l.strip())), None)
    if idx_date is None:
        m = DATE_RE.search(text)
        if not m:
            return None
        review_date = m.group(0)
        # locate its line
        idx_date = next((i for i, l in enumerate(lines) if m.group(0) in l), 0)
    else:
        review_date = lines[idx_date].strip()
    if not any(y in review_date for y in ("2025", "2026")):
        return None  # contract rule 2

    # 2) job title = line above the date (skip a bare rating line)
    job_title = ""
    for j in range(idx_date - 1, -1, -1):
        cand = lines[j].strip()
        if not cand or re.fullmatch(r"\d(?:\.\d)?", cand):
            continue
        job_title = cand
        break
    if not job_title:
        return None

    # 3) tenure/status + location lines after the date
    idx_tenure = None
    status = "Unknown"
    for k in range(idx_date + 1, len(lines)):
        mt = TENURE_RE.search(lines[k])
        if mt:
            idx_tenure = k
            status = "Current" if mt.group(1).lower() == "current" else "Former"
            break
    scan_end = idx_tenure if idx_tenure is not None else min(idx_date + 3, len(lines))
    location = ""
    for k in range(idx_date + 1, scan_end):
        if PH_RE.search(lines[k]):
            location = lines[k].strip()
            break

    # 4) pros / cons by markers (cut at the first trailing UI marker)
    UI_STOP = re.compile(r"\n\s*(?:Helpful\b|Show more\b|Prev\b|Next\b|\d+\s*(?:person|people)\s+found)")
    i_gt = text.find("The good things")
    i_ch = text.find("The challenges")
    pros = cons = ""
    if i_gt != -1:
        start = i_gt + len("The good things")
        end = i_ch if i_ch != -1 else len(text)
        pros = text[start:end]
        mstop = UI_STOP.search(pros)
        if mstop:
            pros = pros[: mstop.start()]
        pros = pros.strip(" \n\t?")
    if i_ch != -1:
        cons = text[i_ch + len("The challenges"):]
        mstop = UI_STOP.search(cons)
        if mstop:
            cons = cons[: mstop.start()]
        cons = cons.strip(" \n\t?")

    # 5) headline = lines between tenure/location block and 'The good things'
    start_line = (idx_tenure + 1) if idx_tenure is not None else scan_end
    headline_lines = []
    for l in lines[start_line:]:
        if "The good things" in l:
            head_part = l.split("The good things", 1)[0].strip()
            if head_part:
                headline_lines.append(head_part)
            break
        if l.startswith("Helpful") or "found this helpful" in l or l.startswith("Show more"):
            break
        headline_lines.append(l)
    review_text = " ".join(headline_lines).strip()

    # ---- contract gates ----
    if not (review_text or pros or cons):
        return None
    if not (CS_IT_RE.search(job_title) and not CS_IT_EXCLUDE.search(job_title)):
        return None
    if not is_ph_location(location):
        return None

    return {
        "review_id": make_id(company, job_title, review_date, review_text or pros, url),
        "company_name": company,
        "job_title": job_title,
        "department": "",
        "seniority_level": "",
        "employment_status": status,
        "review_date": review_date,
        "rating": raw["rating"],
        "review_text": review_text,
        "pros": pros,
        "cons": cons,
        "location": location,
        "source_platform": "jobstreet",
        "source_url": url,
        "scraped_at": now,
    }


def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(json.loads(DONE_FILE.read_text(encoding="utf-8")))
    return set()


def save_done(done: set[str]) -> None:
    DONE_FILE.write_text(json.dumps(sorted(done), indent=0), encoding="utf-8")


def count_csv() -> int:
    if not DATA_CSV.exists():
        return 0
    with open(DATA_CSV, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def append_rows(rows: list[dict]) -> tuple[int, int]:
    DATA_CSV.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if DATA_CSV.exists():
        with open(DATA_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                seen.add(r.get("review_id", ""))
    else:
        with open(DATA_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()
    added = skipped = 0
    with open(DATA_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        for r in rows:
            if r["review_id"] in seen:
                skipped += 1
                continue
            w.writerow({k: r.get(k, "") for k in COLUMNS})
            seen.add(r["review_id"])
            added += 1
    return added, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=600,
                    help="stop once TOTAL rows in csv reach this (default 600)")
    ap.add_argument("--limit", type=int, default=400,
                    help="max companies to visit this run (default 400)")
    ap.add_argument("--sleep", type=float, default=1.8, help="polite delay between pages")
    args = ap.parse_args()

    slugs = json.loads(SLUGS_FILE.read_text(encoding="utf-8"))
    done = load_done()
    # Priority: (1) known big employers, (2) has-reviews + ICT/tech industry,
    # (3) has-reviews + tech name, (4) has-reviews, (5) recent/tech unknown,
    # (9) directory says NO reviews -> skip (unless TOP, caught at 0).
    ICT_IND = {
        "information-technology-services", "computer-software-n-networking",
        "telecommunications-n-internet-service-providers",
        "business-support-services", "employment-services",
        "facilities-management-n-outsourced-services",
        "banking-n-credit", "financial-investment-services", "insurance",
        "consulting-services", "online-media-n-ecommerce",
    }

    def rank(s: dict) -> int:
        slug = s["slug"]
        tech = bool(PRIORITY_RE.search(slug))
        recent = s.get("ts", "") >= "2025"
        ind = s.get("ind") or ""
        if TOP_EMPLOYERS.match(slug):
            return 0
        if s.get("rev") is False:
            return 9
        if s.get("rev"):
            if ind in ICT_IND:
                return 1
            if tech:
                return 2
            return 3
        # rev unknown (not seen by directory enum)
        if tech and recent:
            return 4
        return 5

    todo_rows = sorted((s for s in slugs if s["slug"] not in done), key=rank)
    todo_rows = [s for s in todo_rows if rank(s) != 9]
    todo = [s["slug"] for s in todo_rows]
    todo = todo[: args.limit]
    print(f"slugs={len(slugs)} done={len(done)} todo_this_run={len(todo)} "
          f"rows_now={count_csv()} target={args.target}")

    if not todo:
        print("nothing to do")
        return 0

    from playwright.sync_api import sync_playwright

    now_iso = lambda: datetime.now(timezone.utc).isoformat()
    run_rows: list[dict] = []
    stats = {"pages": 0, "parsed": 0, "kept": 0, "blocked": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        ctx = browser.new_context(locale="en-US")
        page = ctx.new_page()
        try:
            for i, slug in enumerate(todo, 1):
                if count_csv() + len(run_rows) >= args.target:
                    print(f"target {args.target} reached -> stop")
                    break
                url = f"https://ph.jobstreet.com/companies/{slug}/reviews"
                mark = False  # only mark done after a real parse
                try:
                    page.goto(url, timeout=45000, wait_until="domcontentloaded")
                    # wait for review content (or a "no reviews" page)
                    try:
                        page.wait_for_function(
                            "document.body.innerText.includes('The good things') ||"
                            " document.body.innerText.includes('Write a review')",
                            timeout=12000)
                    except Exception:
                        pass
                    page.wait_for_timeout(700)
                    title = page.title().lower()
                    body = page.inner_text("body")
                    if "just a moment" in title or "security verification" in body[:500].lower():
                        stats["blocked"] += 1
                        print(f"[{i}/{len(todo)}] {slug}: CLOUDFLARE CHALLENGE -> waiting")
                        page.wait_for_timeout(8000)
                        page.reload()
                        page.wait_for_timeout(5000)
                        title = page.title().lower()
                        if "just a moment" in title:
                            print("still blocked; pausing 30s")
                            page.wait_for_timeout(30000)
                    data = page.evaluate(JS_PARSE)
                    mark = True
                    company = data.get("company") or slug
                    kept = 0
                    for raw in data.get("reviews", []):
                        stats["parsed"] += 1
                        row = parse_review(raw, company, url, now_iso())
                        if row:
                            run_rows.append(row)
                            kept += 1
                    stats["pages"] += 1
                    stats["kept"] += kept
                    print(f"[{i}/{len(todo)}] {slug}: reviews={len(data.get('reviews', []))} "
                          f"kept={kept} (total_kept={stats['kept']})")
                except Exception as e:  # noqa: BLE001 — one bad page must not kill the run
                    print(f"[{i}/{len(todo)}] {slug}: ERROR {type(e).__name__} {e}")
                finally:
                    if mark:
                        done.add(slug)
                        save_done(done)
                    if run_rows:  # incremental flush — a crash must never cost rows
                        add, skip = append_rows(run_rows)
                        print(f"    flushed {add} rows (+{skip} dup) -> {DATA_CSV.name}")
                        run_rows.clear()
                    time.sleep(args.sleep)
        except KeyboardInterrupt:
            print("\ninterrupted — saving what we have")
        except Exception:
            import traceback
            traceback.print_exc()
            print(f"FATAL in scrape loop — flushing {len(run_rows)} buffered rows")
        finally:
            browser.close()

    added, skipped = append_rows(run_rows) if run_rows else (0, 0)
    print(f"DONE pages={stats['pages']} parsed={stats['parsed']} kept={stats['kept']} "
          f"-> added={added} deduped={skipped} rows_now={count_csv()} -> {DATA_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
