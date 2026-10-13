# Data Diggers — PH Employee Job Reviews (CS/IT)

Scraping pipeline and dataset for **Philippine CS/IT employee job reviews**, built for
the Data Mining summative task.

The published dataset is `data/job_reviews_raw.csv` — **676 records across 15 columns**
covering 319 Philippine employers, collected between 8–9 October 2026 from JobStreet,
GlassDoor, Indeed, and Blind.

---

## Quick start

```bash
# Validate the dataset against the data contract (exit 0 = pass)
python scripts/job_reviews/validate.py

# Regenerate the markdown table from the CSV
python scripts/job_reviews/to_markdown.py

# Merge teammate contribution CSVs from data/incoming/ into the dataset
python scripts/job_reviews/combine.py
```

Run scripts from the repository root so relative paths resolve correctly.

## Layout

```
data/
  job_reviews_raw.csv    the dataset (canonical)
  job_reviews_raw.md     same rows as one markdown table
  incoming/              teammate contribution CSVs (see README there)

docs/
  DATA_CONTRACT.md       schema, validation rules, and access policy

scripts/job_reviews/     the collection pipeline (23 files)
  gates.py               shared schema + record filters
  scrape_*.py            one scraper per platform
  merge_staging.py       fold staging files into the dataset
  clean_rows.py          strip leaked UI fragments
  validate.py            enforce the data contract
  research/              145 one-off exploration scripts (not part of the pipeline)

scripts/job_reviews/README.md   detailed pipeline documentation
```

## How collection works

Each scraper writes to its own staging file, and `merge_staging.py` folds those into
the dataset under the shared gates. Nothing reaches `job_reviews_raw.csv` without
passing validation.

```
scrape_*.py  ->  data/staging_<source>.csv  ->  merge_staging.py  ->  job_reviews_raw.csv
                                                                   ->  clean_rows.py
                                                                   ->  to_markdown.py
                                                                   ->  validate.py
```

Every record is gated on four conditions before it is kept:

| Gate | Requirement |
|---|---|
| Occupation | `job_title` is a CS/IT role |
| Geography | `location` is explicitly Philippine |
| Recency | `review_date` falls in 2025 or 2026 |
| Content | at least one of `review_text` / `pros` / `cons` is non-empty |

All field values are copied **verbatim** from the source. Nothing is fabricated,
translated, or paraphrased.

## Access policy

The pipeline respects each platform's `robots.txt`, paces its requests, and does not
solve CAPTCHAs or bypass bot protection. Where a platform blocks automated access
(GlassDoor, Indeed), the pipeline reads **public Internet Archive snapshots** instead
of circumventing the live site.

See `docs/DATA_CONTRACT.md` for the full rules.

## Requirements

- Python 3.9+
- `playwright`, `requests`, `beautifulsoup4` (only needed to run scrapers;
  validation and export use the standard library)

## Team

Contributions per member are tracked via `data/incoming/` — see
`docs/DATA_CONTRACT.md` section 4.