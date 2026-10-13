"""Probe: JobStreet sitemap (clean path) + structured review DOM parse."""
import json
from playwright.sync_api import sync_playwright

ACCENTURE = "https://ph.jobstreet.com/companies/accenture-168430182370928/reviews"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    ctx = browser.new_context(locale="en-US")
    page = ctx.new_page()

    # 1) sitemap
    for sm in ["https://ph.jobstreet.com/sitemap.xml", "https://ph.jobstreet.com/sitemap_index.xml"]:
        try:
            page.goto(sm, timeout=40000)
            page.wait_for_timeout(1500)
            txt = page.inner_text("body")[:1500]
            print(f"=== {sm} -> {page.url}\n{txt}\n")
        except Exception as e:
            print(f"=== {sm} ERROR {e}")

    # 2) review DOM
    page.goto(ACCENTURE, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(4500)
    body = page.inner_text("body")
    print("=== accenture reviews TITLE:", page.title())
    print("'The good things' count:", body.count("The good things"))
    print("'The challenges' count:", body.count("The challenges"))
    print("2026 mentions:", body.count("2026"), " 2025 mentions:", body.count("2025"))

    # Try to find repeated review containers
    info = page.evaluate("""() => {
        const out = {};
        const selCounts = {};
        for (const sel of ['li','article','div']) {
            selCounts[sel] = document.querySelectorAll(sel).length;
        }
        out.selCounts = selCounts;
        // find elements whose text starts with a helpful-count pattern
        const cands = [...document.querySelectorAll('li, article')].filter(e => /Helpful/.test(e.innerText||''));
        out.helpfulBlocks = cands.length;
        out.samples = cands.slice(0,3).map(e => ({
            tag: e.tagName, cls: e.className, html: e.outerHTML.slice(0, 1500)
        }));
        return out;
    }""")
    print("element counts:", info["selCounts"])
    print("helpfulBlocks:", info["helpfulBlocks"])
    for i, s in enumerate(info["samples"]):
        print(f"--- sample {i} tag={s['tag']} cls={s['cls']}")
        print(s["html"][:1400])
        print()

    browser.close()
