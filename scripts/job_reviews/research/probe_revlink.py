"""Debug: how are 'Reviews' links rendered on directory industry pages?"""
from playwright.sync_api import sync_playwright

URL = "https://ph.jobstreet.com/companies/directory/information-technology-services"

JS = r"""() => {
  const out = {anchors: [], reviewish: [], sample: null};
  document.querySelectorAll('a,button,[role=tab]').forEach(e => {
    const t = (e.innerText || '').trim();
    if (t === 'Reviews') out.anchors.push({
      tag: e.tagName, href: e.getAttribute('href'), cls: e.className,
    });
  });
  out.reviewish = [...document.querySelectorAll("a[href*='reviews']")].slice(0, 6)
    .map(e => e.getAttribute('href'));
  // dump HTML of the first company card
  const a = [...document.querySelectorAll("a[href*='/companies/']")]
    .find(x => /^https?:\/\/[^/]+\/companies\/[a-z0-9\-]+$/.test(x.getAttribute('href') || ''));
  if (a) {
    let n = a;
    for (let i = 0; i < 6 && n.parentElement; i++) n = n.parentElement;
    out.sample = n.outerHTML.slice(0, 1500);
  }
  return out;
}"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()
    pg.goto(URL, timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(3500)
    pg.mouse.wheel(0, 6000)
    pg.wait_for_timeout(1500)
    r = pg.evaluate(JS)
    print("anchors with text 'Reviews':", len(r["anchors"]))
    for x in r["anchors"][:5]:
        print("  ", x)
    print("a[href*='reviews']:", r["reviewish"])
    print("sample card html:\n", r["sample"])
    b.close()
