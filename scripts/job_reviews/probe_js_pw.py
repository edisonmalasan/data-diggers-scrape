"""Can a real Chrome (Playwright channel=chrome, headed) pass JobStreet's Cloudflare?"""
import sys
from playwright.sync_api import sync_playwright

URL = "https://ph.jobstreet.com/companies/sanyo-denki-philippines-inc-168552833061465/reviews"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    ctx = browser.new_context(locale="en-US")
    page = ctx.new_page()
    try:
        page.goto(URL, timeout=45000, wait_until="domcontentloaded")
        for _ in range(6):
            page.wait_for_timeout(2500)
            title = page.title()
            body = page.inner_text("body")
            if "just a moment" not in title.lower() and "checking" not in body[:300].lower():
                break
        print("TITLE:", page.title())
        print("URL:", page.url)
        print("BODY[0:800]:", page.inner_text("body")[:800])
        # count review-ish markers
        for marker in ["The good things", "The challenges", "2026", "current employee", "Helpful"]:
            print(f"marker {marker!r}: {page.inner_text('body').count(marker)}")
    except Exception as e:
        print("ERROR:", type(e).__name__, e)
    browser.close()
