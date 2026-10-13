# Collection Pipeline

The scripts that build `data/job_reviews_raw.csv`. Everything in `research/` is
exploration history and is **not** part of the pipeline.

Run all commands from the repository root.

---

## The flow

```
  scrapers              staging            deliverable
  ────────              ───────            ───────────
  scrape_jobstreet.py ─┐
  scrape_jobstreet_deep│                   job_reviews_raw.csv
  scrape_jobstreet_wb  ├─> data/staging_* ──> merge_staging.py ──> (676 rows)
  scrape_glassdoor     │        .csv                    │
  scrape_glassdoor_live│                   clean_rows.py ──┘
  scrape_indeed_wb     │                          │
  scrape_indeed_wb2 ───┘                          v
  scrape_ph_heavy      data/job_reviews_raw.md <─ to_markdown.py
                                                     │
                                                     v
                                              validate.py (exit 0)
```

`merge_staging.py` is the only path into the dataset. Scrapers never write to
`job_reviews_raw.csv` directly.

---

## Shared module

### `gates.py`
Single source of truth for the contract. Import filters from here so they cannot
drift between scrapers.

| Name | Purpose |
|---|---|
| `COLUMNS` | the 15-column schema, in order |
| `CS_IT_RE` / `CS_IT_EXCLUDE` | occupation gate |
| `PH_RE` / `NON_PH_LOC_RE` / `is_ph_location()` | geography gate |
| `is_cs_it()` / `in_year_window()` / `has_text()` / `has_required_fields()` | record gates |
| `make_id()` / `norm_rating()` | value helpers |

`scrape_jobstreet.py` re-exports these names, so the existing
`from scrape_jobstreet import CS_IT_RE` imports still work.

> The geography gate needs both regexes. `PH_RE` matches the bare token `angeles`,
> so `NON_PH_LOC_RE` rejects `Los Angeles, CA` — a case that appears in real data.

---

## Scrapers

Each writes `data/staging_<source>.csv` and enforces the same gates.

| Script | Source | Notes |
|---|---|---|
| `scrape_jobstreet.py` | JobStreet (live) | Primary source. Playwright. Resumes via `.storage/jobstreet_done.json` |
| `scrape_jobstreet_deep.py` | JobStreet pages 2..N | Reaches 2025 reviews buried below page 1 |
| `scrape_jobstreet_wb.py` | JobStreet via Wayback | Static HTML, BeautifulSoup |
| `scrape_glassdoor.py` | GlassDoor via Wayback | Live access is blocked; uses archived captures |
| `scrape_glassdoor_live.py` | GlassDoor (live) | Anonymous: 3 newest reviews per URL |
| `scrape_indeed_wb.py` | Indeed via Wayback | Reads `comp-initialData` JSON payload |
| `scrape_indeed_wb2.py` | Indeed via Wayback | Second pass with a relaxed country gate |
| `scrape_ph_heavy.py` | Indeed via Wayback | Squeeze pass over PH-heavy MNC pages |
| `collect.py` | Indeed / GlassDoor / JobStreet / LinkedIn | Playwright collector; attaches to your own Chrome via `--cdp` |
| `login.py` | — | Saves a browser session for `collect.py` |

Reusable helpers: `siteb_lib.py` (polite fetch) and `blind_extract.py` (Blind payload parser).

```bash
python scripts/job_reviews/scrape_jobstreet.py --target 600
python scripts/job_reviews/merge_staging.py
```

---

## Data assembly

| Script | Purpose |
|---|---|
| `merge_staging.py` | Fold `data/staging_*.csv` into the dataset. Dedupes by `review_id` **and** by content fingerprint. `--purge` deletes staging files after a successful merge |
| `combine.py` | Merge teammate CSVs from `data/incoming/` under the same gates |
| `clean_rows.py` | Strip leaked UI fragments (`Helpful?`, `Show more`, `N person`) from `pros`/`cons`/`review_text`. Idempotent |
| `drop_nonph.py` | Scrub any non-PH location that predates the geography gate |
| `to_markdown.py` | Regenerate `job_reviews_raw.md` from the CSV |
| `validate.py` | Enforce `docs/DATA_CONTRACT.md` section 3. Exit 0 = pass |

```bash
python scripts/job_reviews/merge_staging.py
python scripts/job_reviews/clean_rows.py
python scripts/job_reviews/to_markdown.py
python scripts/job_reviews/validate.py
```

### What `validate.py` checks

1. `review_id` unique
2. `review_date` within 2025 or 2026
3. `location` not explicitly foreign
4. at least one of `review_text` / `pros` / `cons` non-empty
5. required fields non-empty
6. `source_url` starts with `http`
7. warns below 200 rows

---

## Tests

`test_country_gate.py`, `test_extract.py`, `test_gd.py` — runnable directly with
`python`, no pytest required.

---

## Conventions

- **Verbatim data.** Field values are copied exactly as shown on the source. No
  fabrication, translation, or rewording.
- **Never hand-edit** `job_reviews_raw.csv` or the `.md`. Both are generated.
- **Resumable.** Scrapers checkpoint to `.storage/` and can be re-run safely.
- **Idempotent.** Merge, clean, and validate can all run repeatedly.
- `.storage/` is gitignored — it holds HTML dumps, logs, and Chrome profiles with
  session cookies. Nothing in it should ever be committed.