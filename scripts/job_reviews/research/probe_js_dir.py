"""Explore JobStreet /companies directory: structure, filters, pagination, robots."""
from playwright.sync_api import sync_playwright
import requests
import re

ROBOTS = "https://ph.jobstreet.com/robots.txt"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    ctx = browser.new_context(locale="en-US")
    page = ctx.new_page()

    # robots via the same browser (plain requests get CF)
    page.goto(ROBOTS, timeout=45000)
    print("=== ROBOTS.TXT ===")
    print(page.inner_text("body")[:2500])

    page.goto("https://ph.jobstreet.com/companies", timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    print("=== /companies TITLE:", page.title())
    body = page.inner_text("body")
    print(body[:3000])
    print("=== links with 'companies/' hrefs (first 40):")
    hrefs = page.eval_on_selector_all(
        "a[href*='/companies/']", "els => els.map(e => e.getAttribute('href'))")
    seen = []
    for h in hrefs:
        if h not in seen:
            seen.append(h)
    for h in seen[:40]:
        print("   ", h)
    print("total company links:", len(seen))

    # look for pagination or sort controls
    controls = page.eval_on_selector_all(
        "button, a[role=button]",
        "els => els.map(e => (e.innerText||'').trim()).filter(t => t && t.length < 40)")
    print("=== buttons/controls:", controls[:60])

    # check page 2
    page.goto("https://ph.jobstreet.com/companies?page=2", timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(3500)
    hrefs2 = page.eval_on_selector_all(
        "a[href*='/companies/']", "els => els.map(e => e.getAttribute('href'))")
    seen2 = list(dict.fromkeys(hrefs2))
    print("=== page2 title:", page.title(), "company links:", len(seen2))
    for h in seen2[:10]:
        print("   ", h)
    overlap = set(seen) & set(seen2)
    print("overlap with page1:", len(overlap))

    browser.close()
