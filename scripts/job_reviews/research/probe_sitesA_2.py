"""Site-group A probe 2: jobsdb country domains, talenttribe structure,
monster/foundit review presence, careerbuilder variants. Requests only."""
import re
import time
import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
     "Accept-Language": "en-US,en;q=0.9"}

def get(url, timeout=40):
    try:
        return requests.get(url, headers=H, timeout=timeout, allow_redirects=True)
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {e}")
        return None

def summarize(url, kws=("review", "employee review", "company review")):
    print("-" * 60)
    print("URL:", url)
    r = get(url)
    if r is None:
        return None
    print("status:", r.status_code, "-> final:", r.url)
    txt = r.text[:300000]
    m = re.search(r"<title[^>]*>(.*?)</title>", txt, re.S | re.I)
    print("title:", (m.group(1).strip()[:140] if m else "(none)"))
    low = txt.lower()
    print("len:", len(r.text), {k: low.count(k) for k in kws})
    return r

# --- jobsdb country domains ---
print("=== JOB SDB DOMAIN MAP ===")
for u in [
    "https://www.jobsdb.com/",
    "https://www.jobsdb.com/hk",
    "https://www.jobsdb.com/my",
    "https://www.jobsdb.com/sg",
    "https://www.jobsdb.com/th",
    "https://www.jobsdb.com/id",
    "https://www.jobsdb.com/ph",
    "https://ph.jobsdb.com/",
    "https://www.jobsdb.com.ph/",
    "https://jobsdb.com.ph/",
]:
    summarize(u)
    time.sleep(2.5)

# --- talenttribe structure ---
print("\n=== TALENTTRIBE ===")
for u in [
    "https://talenttribe.asia/",
    "https://talenttribe.asia/companies/talenttribe",
    "https://talenttribe.asia/sitemap.xml",
    "https://talenttribe.asia/robots.txt",
]:
    summarize(u, kws=("review", "testimonial", "philippin", "manila", "cebu"))
    time.sleep(2.5)

# --- monster/foundit ---
print("\n=== MONSTER / FOUNDIT ===")
for u in [
    "https://www.monster.com/",
    "https://www.foundit.com.ph/",
    "https://www.foundit.com.ph/robotxt",  # some foundit robots paths
]:
    summarize(u, kws=("review", "company profile", "employer"))
    time.sleep(2.5)

# --- careerbuilder ---
print("\n=== CAREERBUILDER ===")
for u in [
    "https://www.careerbuilder.com/reviews",
    "https://www.careerbuilder.com/company-reviews",
    "https://www.careerbuilder.com/cmp/",
    "https://www.careerbuilder.com.ph",
    "https://ph.careerbuilder.com/",
    "https://www.careerbuilder.com.sg/",
    "https://www.careerbuilder.com.my/",
]:
    summarize(u, kws=("review", "employer", "company profile"))
    time.sleep(2.5)
print("DONE")
