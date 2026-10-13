# Research Scripts

**Not part of the collection pipeline.** These 145 scripts are one-off exploration
artifacts kept for provenance — they document how the dataset was found and why
certain sources were rejected.

Nothing here runs automatically, and the pipeline does not import any of it.
The scripts that build the dataset live one directory up; see `../README.md`.

---

## What they are

During collection we probed candidate sources to answer three questions:

1. Does this platform serve Philippine reviews?
2. Does it allow automated access, and if not, is there a public archive?
3. Is the data usable under the contract's CS/IT + PH + date gates?

Most of them printed a short verdict. Their value is the record of *which sources
were tried and ruled out* — useful for the limitations section of the report, and
for anyone extending the pipeline later.

## Naming conventions

| Prefix | Meaning |
|---|---|
| `probe_*.py` | reachability / structure probes against a candidate source |
| `diag_*.py` | funnel diagnostics — how many records died at each gate, and why |
| `inspect_*.py` | one-off inspection of a saved dump |
| `analyze_*.py`, `enum_*.py`, `build_*.py` | enumerate URLs / slugs / employer lists |
| `find_*.py` | locate specific records |
| `test_*.py`, `debug_js.py`, `prune_lost_jobstreet.py` | ad-hoc checks kept from debugging |

Numbered variants (`probe_b_blind2.py` … `probe_b_blind17.py`,
`probe_gd_dom.py`, `probe_gd_dom3.py`) are successive attempts at the same
question. Only the last one in a series is meaningful; the earlier ones document
the path that got there.

## Known findings

Recorded in `.storage/*.md` (not committed, since `.storage/` is gitignored):

- **GlassDoor** — live access hard-blocks automated requests. Archived captures work.
- **Indeed** — live is bot-blocked, but Wayback captures carry a full
  `comp-initialData` JSON payload including `country` and `overallRating`.
- **Blind** — reviews sit in a Next.js flight payload (`self.__next_f`), not the DOM.
- **Handshake, Fishbowl, Wellfound, Reddit, Layoff, WTTJ, TotalJobs, StepStone** and
  others were evaluated and rejected — no usable PH CS/IT review data, or no
  automated access.

## Running one

These target live sites and most will fail or return nothing now. They are kept as
a record, not as tooling. Where a script needs sibling imports, it adds the
pipeline directory to `sys.path` itself.

Anything that writes output resolves `.storage/` one level up, in
`scripts/job_reviews/.storage/`.

---

If you extend the collection, add new **scrapers** to the parent directory and
follow `../README.md`. Keep probes here.