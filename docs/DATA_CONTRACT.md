# Data Contract — PH Employee Job Reviews (CS/IT)

Group: DATA DIGGERS · Topic: Job Reviews
Deliverable: `data/job_reviews_raw.csv` + `data/job_reviews_raw.md` (one table only, with headings).

> Note: this file was recreated on 2026-10-09 after the original was lost in a
> file cleanup; content reflects the rules the pipeline had been enforcing,
> plus the user-approved date-window update (2025 added).

## 1. Output files

- `data/job_reviews_raw.csv` — the canonical dataset (append-only merge, dedupe by `review_id`).
- `data/job_reviews_raw.md` — same rows as ONE markdown table with headings.
- Staging files (`data/staging_*.csv`) are merged in by `scripts/job_reviews/merge_staging.py`; raw is only rewritten by the merge/finalize chain.

## 2. Schema (15 columns, exact order)

| # | column | meaning |
|---|---|---|
| 1 | review_id | unique, stable id (derived verbatim from source; never reuse) |
| 2 | company_name | employer name as shown on the source |
| 3 | job_title | reviewer's job title as shown on the source |
| 4 | department | reviewer's department if shown, else empty |
| 5 | seniority_level | if shown, else empty |
| 6 | employment_status | e.g. Full Time / Part Time / Contract, if shown |
| 7 | review_date | date of the review — **must fall in 2025 or 2026** |
| 8 | rating | overall rating if shown (keep source scale) |
| 9 | review_text | free-text body if shown |
| 10 | pros | pros text if shown |
| 11 | cons | cons text if shown |
| 12 | location | reviewer's location **explicitly as shown** (must be a PH location) |
| 13 | source_platform | platform name (e.g. jobstreet, Glassdoor, Indeed, Blind) |
| 14 | source_url | canonical URL the row came from |
| 15 | scraped_at | ISO-8601 timestamp of extraction |

## 3. Validation rules (enforced by `scripts/job_reviews/validate.py`)

1. `review_id` must be unique across the file.
2. `review_date` must be in **2025 or 2026**.
3. `location` must be **explicitly a Philippine location** — never guessed from company HQ or source domain.
4. At least one of `review_text` / `pros` / `cons` must be non-empty.
5. `job_title` must be a CS/IT role (shared `CS_IT_RE` / `CS_IT_EXCLUDE` gates in `scrape_jobstreet.py`).
6. Required non-empty columns: `review_id`, `company_name`, `job_title`, `review_date`, `location`, `source_platform`, `source_url`, `scraped_at`.
7. At least **200 usable unique records** (500–1000 preferred).
8. All text fields are **verbatim** — no fabrication, no translation, no cleanup beyond whitespace.
9. Respect site robots/politeness: crawl only permitted paths, pace requests, no login/CAPTCHA-solving.
10. Validator must exit 0 (`python scripts/job_reviews/validate.py`).

## 4. Team contribution workflow

- One CSV per member in `data/incoming/` (see its README), header from raw; 17-col supersets are projected to 15 by the merge.
- Never commit fake rows. Team files are merged via `EXTRA_FILES` in `merge_staging.py` under the same gates.
