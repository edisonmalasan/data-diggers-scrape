"""Debug: show per-review parse + filter decisions for a JobStreet slug."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_jobstreet import JS_PARSE, DATE_RE, PH_RE, CS_IT_RE, CS_IT_EXCLUDE, parse_review  # noqa: E402

from playwright.sync_api import sync_playwright

SLUG = sys.argv[1] if len(sys.argv) > 1 else "8telcom-168553930231816"
URL = f"https://ph.jobstreet.com/companies/{SLUG}/reviews"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()
    pg.goto(URL, timeout=45000, wait_until="domcontentloaded")
    try:
        pg.wait_for_function(
            "document.body.innerText.includes('The good things') ||"
            " document.body.innerText.includes('Write a review')", timeout=12000)
    except Exception:
        pass
    pg.wait_for_timeout(700)
    data = pg.evaluate(JS_PARSE)
    print("company:", repr(data.get("company")))
    for n, raw in enumerate(data["reviews"], 1):
        print(f"\n--- review {n}: rating={raw['rating']!r}")
        print("LINES:", raw["lines"][:12])
        row = parse_review(raw, data.get("company") or "?", URL, "2026-01-01T00:00:00")
        if row is None:
            # figure out why
            lines = raw["lines"]
            text = raw["text"]
            idx_date = next((i for i, l in enumerate(lines) if DATE_RE.fullmatch(l.strip())), None)
            if idx_date is None:
                print("REJECT: no date line | DATE_RE.search:", DATE_RE.search(text))
            else:
                d = lines[idx_date].strip()
                if "2026" not in d:
                    print(f"REJECT: date not 2026 -> {d!r}")
                else:
                    job = ""
                    for j in range(idx_date - 1, -1, -1):
                        c = lines[j].strip()
                        if c and not re.fullmatch(r"\d(?:\.\d)?", c):
                            job = c
                            break
                    scan_end = min(idx_date + 3, len(lines))
                    loc = ""
                    for k in range(idx_date + 1, scan_end):
                        if PH_RE.search(lines[k]):
                            loc = lines[k].strip()
                            break
                    it_ok = bool(CS_IT_RE.search(job)) and not CS_IT_EXCLUDE.search(job)
                    print(f"REJECT: date={d!r} job={job!r} cs_it={it_ok} "
                          f"cs_match={CS_IT_RE.search(job)} excl={CS_IT_EXCLUDE.search(job)} "
                          f"loc={loc!r} ph={bool(loc and PH_RE.search(loc))}")
        else:
            print("KEPT:", {k: row[k] for k in
                            ("company_name", "job_title", "review_date", "rating",
                             "employment_status", "location", "review_text", "pros", "cons")})
    b.close()
