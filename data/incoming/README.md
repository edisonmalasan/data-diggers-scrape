# Member Contributions

Drop **one CSV per member** here, named after them — e.g. `malasan.csv`,
`espartinas.csv`. They get merged into the dataset with:

```bash
python scripts/job_reviews/combine.py
```

## Rules

1. **Copy the header line** from `../job_reviews_raw.csv` — the 15 contract columns,
   in order. Extra columns are projected away automatically.
2. **Never commit fabricated rows.** Every field must be copied verbatim from the
   platform you collected it from, and every row needs a working `source_url`.
3. **One file per member.** This keeps the merge report meaningful — it prints
   kept/dropped counts per file.

## What gets dropped

`combine.py` silently skips (and reports) rows that fail the contract:

- no `review_text`, `pros`, or `cons`
- a `review_date` outside 2025–2026
- a missing required field (`company_name`, `job_title`, `review_date`,
  `location`, `source_platform`, `source_url`)

Missing `review_id` values are generated for you. Missing `scraped_at` is stamped
with the current UTC time.

## After merging

```bash
python scripts/job_reviews/to_markdown.py
python scripts/job_reviews/validate.py
```

`validate.py` must exit 0. Full rules live in `../../docs/DATA_CONTRACT.md`.