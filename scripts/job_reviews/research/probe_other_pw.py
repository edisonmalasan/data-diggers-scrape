"""Do fresh Playwright Chrome instances clear Indeed/Glassdoor (no bypass tricks)?"""
from playwright.sync_api import sync_playwright

TARGETS = [
    ("indeed", "https://ph.indeed.com/cmp/Accenture/reviews"),
    ("glassdoor", "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"),
    ("careerbliss-dates", "https://www.careerbliss.com/accenture/reviews/?page=2"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    ctx = browser.new_context(locale="en-US")
    for name, url in TARGETS:
        page = ctx.new_page()
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            for _ in range(5):
                page.wait_for_timeout(2500)
                t = page.title().lower()
                if "just a moment" not in t and "security" not in t and "moment" not in t:
                    break
            body = page.inner_text("body")
            print(f"\n=== {name}: TITLE={page.title()[:70]!r} len={len(body)}")
            print("   head:", " | ".join(body.split("\n")[:12])[:400])
            for m in ["Pros", "Cons", "2026", "Manila", "employee", "additional verification",
                      "captcha", "Show more", "Posted"]:
                c = body.count(m)
                if c:
                    print(f"   {m!r}: {c}")
        except Exception as e:
            print(f"\n=== {name}: ERROR {type(e).__name__} {e}")
        page.close()
    browser.close()
