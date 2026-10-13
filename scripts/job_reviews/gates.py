"""Shared contract schema and record gates for the job-reviews pipeline.

This module is the single source of truth for:
  - COLUMNS            the 15-column dataset schema
  - CS_IT_RE / CS_IT_EXCLUDE   occupation gate (must be a CS/IT role)
  - PH_RE / NON_PH_LOC_RE / is_ph_location()   geography gate (must be PH)
  - make_id()          stable SHA-1 record identifier
  - norm_rating()      rating-scale normalization
  - required_text()    the "at least one body field" check

Every scraper imports its gates from here so the filters can never drift apart.
`scrape_jobstreet.py` re-exports these names, so older imports of the form
`from scrape_jobstreet import CS_IT_RE, is_ph_location` keep working.

Contract: docs/DATA_CONTRACT.md section 3.
"""
from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------- schema ----

COLUMNS = [
    "review_id", "company_name", "job_title", "department",
    "seniority_level", "employment_status", "review_date", "rating",
    "review_text", "pros", "cons", "location",
    "source_platform", "source_url", "scraped_at",
]

# Fields that must be non-empty for a row to be usable (contract rule 6).
REQUIRED = [
    "company_name", "job_title", "review_date",
    "location", "source_platform", "source_url",
]

# The review year window (contract rule 2).
ALLOWED_YEARS = ("2025", "2026")


# ------------------------------------------------------- occupation gate ----

# Positive: the title must contain a CS/IT phrase. A bare 'engineer' or
# 'developer' is NOT enough (Mechanical/Civil engineers are not CS/IT) — the
# match must be CS-qualified, e.g. 'software engineer' or 'data analyst'.
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

# Hard rejects: unmistakably non-CS/IT professions. Checked against the title.
# Bare 'engineer'/'architect' need no exclusion — CS_IT_RE only matches
# CS-qualified forms, so 'Mechanical Engineer' fails the positive gate alone.
CS_IT_EXCLUDE = re.compile(
    r"mechanical|electrical|civil|chemical|industrial|mechatronic|"
    r"production|manufacturing|maintenance|quality control inspector|"
    r"nurse|accountant|cashier|driver|waiter|cook|security guard|"
    r"marketing|sales|account executive|customer service|call center|"
    r"\bhr\b|human resource|recruiter|finance|payroll|legal|administrative|"
    r"supply chain|warehouse|logistics|purchasing|procurement|teacher",
    re.I,
)


# ------------------------------------------------------- geography gate ----

# The location string must name a Philippine place or region.
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

# Defense-in-depth: explicit US/foreign markers. Guards against a PH_RE false
# positive, e.g. "Los Angeles, CA" matching the bare token "angeles".
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


def is_cs_it(title: str | None) -> bool:
    """True when the job title names a CS/IT role."""
    if not title:
        return False
    return bool(CS_IT_RE.search(title)) and not CS_IT_EXCLUDE.search(title)


# ----------------------------------------------------- content gates ----

def in_year_window(date: str | None) -> bool:
    """True when the review date falls inside the allowed year window."""
    return bool(date) and any(y in date for y in ALLOWED_YEARS)


def has_text(row: dict) -> bool:
    """True when at least one of the three body fields is non-empty (rule 4)."""
    body = "".join(
        (row.get(f) or "")
        for f in ("review_text", "pros", "cons")
    )
    return bool(body.strip())


def has_required_fields(row: dict) -> bool:
    """True when every field in REQUIRED is non-empty (rule 6)."""
    return all((row.get(f) or "").strip() for f in REQUIRED)


# --------------------------------------------------------- value helpers ----

def make_id(company: str, title: str, date: str, text: str, url: str) -> str:
    """Stable identifier: SHA-1 over company|title|date|text[:120]|url."""
    raw = "|".join([company, title, date, text[:120], url]).encode("utf-8")
    return "rv_" + hashlib.sha1(raw).hexdigest()[:12]


def norm_rating(raw: str | None) -> str:
    """Normalize '4.0/5', '4 out of 5', '80/100' to a 1-5 float string.

    Returns '' when the rating cannot be parsed.
    """
    if not raw:
        return ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:/|out of\s+)?\s*(\d+)?", raw)
    if not m:
        return ""
    val, scale = float(m.group(1)), float(m.group(2) or 5)
    if scale == 100:      # e.g. "80/100" -> 4.0
        val = val / 20
    elif scale == 10:     # e.g. "7/10"   -> 3.5
        val = val / 2
    return f"{min(5.0, max(1.0, val)):.1f}"