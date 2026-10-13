"""Offline unit test for the fixed country gate in scrape_indeed_wb.build_row."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scrape_indeed_wb import build_row  # noqa: E402

GATES = ["drop_date", "drop_text", "drop_csit", "drop_country",
         "drop_location", "drop_meta"]


def mk(**kw):
    it = {"jobTitle": "Software Engineer",
          "submissionDate": "March 5, 2026",
          "text": "Great place to work as an engineer.",
          "_company": "Acme",
          "location": "Makati, Philippines",
          "sharingLink": "https://ph.indeed.com/cmp/Acme/reviews/x?id=1"}
    it.update(kw)
    return it


def t(label, it, page_is_ph, expect):
    s = {k: 0 for k in GATES + ["items", "kept"]}
    row = build_row(it,
                    "https://web.archive.org/web/20260901/https://ph.indeed.com/cmp/Acme/reviews",
                    "2026-10-09T00:00:00+00:00", s, page_is_ph=page_is_ph)
    gate = next((g for g in GATES if s[g]), "KEPT")
    got = "KEPT" if row else "drop@" + gate
    ok = "ok " if got == expect else "FAIL"
    print(f"[{ok}] {label:48} -> {got} (expected {expect})")
    return row


t("PH page, country missing", mk(country=None), True, "KEPT")
t("PH page, country empty string", mk(country="  "), True, "KEPT")
t("PH page, country PH", mk(country="PH"), True, "KEPT")
t("PH page, country ph (lowercase)", mk(country="ph"), True, "KEPT")
t("PH page, country US -> must reject", mk(country="US"), True, "drop@drop_country")
t("PH page, country IN -> must reject", mk(country="IN"), True, "drop@drop_country")
t("non-PH page, country missing -> reject", mk(country=None), False, "drop@drop_country")
t("non-PH page, country empty -> reject", mk(country=""), False, "drop@drop_country")
t("non-PH page, country PH -> keep", mk(country="PH"), False, "KEPT")
t("PH page, non-2026 date drops first", mk(country="PH", submissionDate="April 2, 2025"), True, "drop@drop_date")
t("PH page, empty text drops second", mk(country="PH", text=""), True, "drop@drop_text")
t("PH page, CSR title excluded", mk(country="PH", jobTitle="Customer Service Representative"), True, "drop@drop_csit")
t("PH page, non-CS/IT title excluded", mk(country="PH", jobTitle="Accounting Clerk"), True, "drop@drop_csit")
t("PH page, foreign location rejected", mk(country="PH", location="New York, NY"), True, "drop@drop_location")
t("PH page, empty location rejected", mk(country="PH", location=""), True, "drop@drop_location")

row = t("full keep row shape", mk(country="PH"), True, "KEPT")
print("row keys:", sorted(row.keys()))
print("date:", row["review_date"], "| platform:", row["source_platform"],
      "| rating:", repr(row["rating"]), "| status:", row["employment_status"])
