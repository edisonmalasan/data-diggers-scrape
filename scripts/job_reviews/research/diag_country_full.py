# -*- coding: utf-8 -*-
"""Full tally of country values across every fetched page, and specifically for
date+csit+text passers (the 111 drop_country). Decisive test: does country='PH'
(or empty) ever appear on www.indeed.com pages?"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrape_indeed_wb import (
    CS_IT_EXCLUDE, CS_IT_RE, DATE_OK_RE, extract_items, is_ph_location, load_json,
    log,
)

STORAGE = os.path.join(os.path.dirname(__file__), "..", ".storage")

done = load_json(os.path.join(STORAGE, "indeed_wb_done3.json"), {})

# country histogram: all items + passers-only (date+csit+text)
from collections import Counter
all_c = Counter()
passer_c = Counter()
passer_examples = []
ph_items = 0
www_items = 0
for url, ent in done.items():
    items = extract_items(ent.get("html", ""))
    page_is_ph = (ent.get("host") == "ph.indeed.com") or ("fcountry=ph" in url.lower())
    for it in items:
        if page_is_ph:
            ph_items += 1
        else:
            www_items += 1
        all_c[it.get("country") or "<empty>"] += 1
        text = " ".join((it.get(k) or "").strip() for k in ("review_text", "pros", "cons")).strip()
        title = (it.get("job_title") or "").strip()
        if (DATE_OK_RE.search(it.get("date") or "") and text
                and CS_IT_RE.search(title) and not CS_IT_EXCLUDE.search(title)):
            c = it.get("country") or "<empty>"
            passer_c[c] += 1
            if c == "PH" or (c == "<empty>" and page_is_ph) or len(passer_examples) < 10:
                passer_examples.append((c, page_is_ph, title[:30], (it.get("date") or "")[:16],
                                        (it.get("location") or "")[:30], url))

log("fetched pages: %d (ph items %d, www items %d)" % (len(done), ph_items, www_items))
log("ALL items country histogram: %s" % dict(all_c.most_common()))
log("date+csit+text PASSERS country histogram: %s" % dict(passer_c.most_common()))
log("passer examples:")
for e in passer_examples:
    log("  country=%s page_is_ph=%s | %s | %s | %s | %s" % e)
