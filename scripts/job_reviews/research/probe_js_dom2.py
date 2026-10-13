"""Map JobStreet review container DOM: walk up from 'The good things' label."""
from playwright.sync_api import sync_playwright

ACCENTURE = "https://ph.jobstreet.com/companies/accenture-168430182370928/reviews"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    ctx = browser.new_context(locale="en-US")
    page = ctx.new_page()
    page.goto(ACCENTURE, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(4500)

    res = page.evaluate("""() => {
        // find the text node elements containing exactly the label
        const labels = [...document.querySelectorAll('div,span,p,h1,h2,h3,h4')]
            .filter(e => (e.innerText||'').trim() === 'The good things');
        if (!labels.length) return {err: 'no label'};
        const lab = labels[0];
        // walk up until ancestor contains a date (e.g. 2026) and a helpful marker
        let node = lab, hops = [];
        for (let i = 0; i < 8 && node; i++) {
            const t = (node.innerText || '');
            hops.push({
                depth: i, tag: node.tagName, cls: String(node.className).slice(0,120),
                len: t.length, has2026: /2026/.test(t), hasHelpful: /Helpful/.test(t),
                head: t.replace(/\\s+/g,' ').slice(0, 220)
            });
            node = node.parentElement;
        }
        return {labels: labels.length, hops};
    }""")
    import json
    print(json.dumps(res, indent=1)[:4000])

    # dump outerHTML of the best container (the one containing a 2026 date + helpful)
    html = page.evaluate("""() => {
        const labels = [...document.querySelectorAll('div,span,p')]
            .filter(e => (e.innerText||'').trim() === 'The good things');
        let node = labels[0];
        for (let i = 0; i < 8 && node; i++) {
            const t = node.innerText || '';
            if (/2026/.test(t) && /Helpful/.test(t) && t.length < 4000) return node.outerHTML;
            node = node.parentElement;
        }
        return labels[0].parentElement.parentElement.outerHTML;
    }""")
    print("\n=== CONTAINER HTML (first 3500 chars) ===")
    print(html[:3500])
    browser.close()
