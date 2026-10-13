# Job Reviews — local runner (your PC, your logins)

The agent sandbox cannot reach your logged-in Orca/Chrome sessions
(`runtime_access_denied`) and Indeed/Glassdoor return 403 to server-side
fetches. So collection runs **here on your PC**, reusing your Chrome profile.

## 1. Setup (once)

```powershell
pip install -r scripts/job_reviews/requirements.txt
playwright install chrome
```

## 2. Attach YOUR Chrome (recommended — your logins apply)

`login.py` opens a stranger browser: fresh profile, zero cookies, and
Indeed's anti-bot rejects automated sign-ins there ("Something went
wrong"). Attaching your real Chrome skips login entirely.

```powershell
# 1. Close Chrome completely (one time)
# 2. Reopen it with automation access (keep this window open the whole run):
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data"
# 3. In that window, confirm Indeed/Glassdoor show you logged in.
# 4. VERIFY SEED URLs FIRST (important): open each URL in companies.seed.json
#    in your normal browsing. If a page 404s or shows no reviews, replace the
#    URL with the real reviews page you can see (copy from the address bar).
#    The Glassdoor links above are guesses — fix them this way. LinkedIn and
#    JobStreet company pages are NOT review feeds, so they are manual-only
#    (section 5) and were removed from the seeds.
# 5. Then check + scrape:
```

## 3. VERDICT on automation (confirmed 2026-10-08)

`--check --cdp` output showed every Indeed tab titled **"Just a moment..."**
with text *"additional verification required / your ray id"* — that is
Cloudflare's bot challenge, served to script-driven tabs while your manual
tabs pass. Bypassing it would violate contract rule 9 (collect only what the
site permits), so **automation is closed for Indeed, Glassdoor, and LinkedIn**.
Do not spend more time on selectors or logins — go to section 5.

## 4. Manual collection — the way to 200+ (7 members × 30 rows = 210)

Each member copies genuine reviews BY HAND from their own logged-in browser
into `data/incoming/<lastname>.csv` (headers = same 15 contract columns;
copy the header line from `data/job_reviews_raw.csv`). Rules:

1. CS/IT `job_title` only (software, data, network, QA, DevOps, IT support…).
2. PH `location` only — must name a PH city/region or Philippines.
3. `review_date` within 2026 only — skip undated/older reviews.
4. Copy `review_text` (and `pros`/`cons` where shown) VERBATIM. Never invent.
5. Every row needs its real `source_url` (page you copied from) and
   `source_platform` (indeed / glassdoor / jobstreet / linkedin / kalibrr …).
6. `rating` 1–5 if the site shows one, else leave empty. Never guess.
7. Suggested split (30 each): MALASAN Indeed Accenture/IBM · ESPARTINAS
   Indeed Infosys/Cognizant · CASILEN Indeed DXC/local banks-telcos ·
   AGUSTIN Glassdoor tech · ALCAZAR Glassdoor tech · BAG-EO JobStreet/Kalibrr ·
   LOPEZ LinkedIn posts + any PH site. Any CS/IT PH 2026 review counts
   regardless of site — quotas matter more than assignments.

   Widened hunting grounds (automation probed 2026-10-08, all bot-walled
   except Comparably — and Comparably publishes NO dates or locations, so it
   fails contract rules 2–3; cite it in the paper as an excluded source):
   - Indeed PH pre-filtered (paste in normal Chrome, copy by hand):
     `https://ph.indeed.com/cmp/<Company>/reviews?fjobtitle=Software+Engineer&fcountry=PH&floc=Philippines`
   - Glassdoor Manila-specific pages, e.g.
     `https://www.glassdoor.com/Reviews/ING-Hubs-Philippines-Senior-Software-Engineer-Manila-Reviews-EI_IE9047100.0,20_KO21,45_IL.46,52_IM995.htm`
     (search `site:glassdoor.com Manila <role> Reviews` for more).
   - Reddit (public, datable, URL-traceable — rating stays empty):
     r/PinoyProgrammer, r/phcareers, r/PHJobs company-experience threads.
     Mapping: `review_date` = post date (must be 2026), `location` = PH place
     named in the post else `Philippines` only if PH context is explicit,
     `employment_status` = Unknown, `source_platform` = reddit,
     `source_url` = thread URL. Skip memes and job ads.
   - Facebook hiring/experience groups you already belong to (same mapping as
     Reddit, `source_platform` = facebook).
   - Kalibrr/Bossjob/Glints carry job ADS, not reviews — do not log ads as
     reviews (contract rule 8).

When all files are in, the owner (Edison) runs:

```powershell
python scripts/job_reviews/combine.py
python scripts/job_reviews/to_markdown.py
python scripts/job_reviews/validate.py
```

`combine.py` merges, drops non-2026/incomplete rows (reported per file),
dedups by `review_id`, and writes `data/job_reviews_raw.csv`.
`to_markdown.py` rebuilds the one-table `data/job_reviews_raw.md`.
`validate.py` must exit 0 with ≥200 rows.

## Notes per site

- **Indeed PH** (`ph.indeed.com/cmp/.../reviews`): first pages public,
  deeper pages need login.
- **Glassdoor**: login required; keep requests ≥3 s apart.
- **JobStreet/SEEK**: company pages hold brand info; reviews are thin —
  record only genuine employee-review text, leave `rating` empty if absent.
- **LinkedIn**: no star-rating review feed; record only posts clearly
  written as employee reviews, `rating` empty, `source_url` = post URL.
