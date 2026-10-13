"""Build .storage/gd_live_targets.json — curated + discovered employers.

Order (the scraper walks top-down):
  1. CURATED_PH      PH-dedicated / PH-heavy employers (highest P(location=PH))
  2. CURATED_MULTI   BPOs + IT multinationals with PH delivery centers
  3. rest            named pages from the 2026 Wayback set (deduped by E-id,
                     shortest slug wins), minus already-included E-ids
Also resolves 'PAL' (eid learned from gd_ph_eids.json).
"""
import json
import re
from pathlib import Path

STORAGE = Path(__file__).resolve().parents[1] / ".storage"

PAT = re.compile(r"/Reviews/([A-Za-z0-9%.\-_ ]+?)-Reviews-(?:E|EI_IE)(\d+)")

# ---- curated, verified against CDX captures (slug = canonical, eid) ----
CURATED_PH = [
    ("Teleperformance-Philippines", "348159"),
    ("Teleperformance", "9779"),
    ("Globe-Telecom", "42313"),
    ("PLDT", "522218"),
    ("Smart-Communications", "390488"),
    ("Jollibee", "22569"),
    ("Ayala", "42283"),
    ("Ayala-Land", "472521"),
    ("Ayala-Systems-Technology", "386235"),
    ("BDO", "7508"),
    ("Bank-of-the-Philippine-Islands", "11900"),
    ("Unionbank-of-the-Philippines", "473455"),
    ("Eastwest-Banking", "586059"),
    ("Robinsons-Land", "591975"),
    ("Manila-Water", "591497"),
    ("Meralco", "8314"),
    ("ABS-CBN", "42223"),
    ("GMA-Network", "472017"),
    ("Insular-Life", "1103044"),
    ("Nestle-Philippines", "472639"),
    ("JGC-Philippines", "303694"),
    ("HSBC-Electronic-Data-Processing-Philippines", "637166"),
    ("Asticom-Technologies", "1523794"),
    ("Sykes-Asia-Cebu", "579457"),
    ("Everise", "411039"),
    ("MicroSourcing-International", "404596"),
    ("Cloudstaff", "1276771"),
    ("Energy-Development", "561910"),
    ("First-Gen-Management", "701630"),
    ("Shopee", "1263091"),
    ("Lazada", "578726"),
    ("Standard-Chartered", "10238"),
    ("Cebu-Pacific", "398568"),
    ("Sunlife-Financial", "301218"),
]

CURATED_MULTI = [
    ("Accenture", "4138"), ("IBM", "354"), ("Cognizant", "8014"),
    ("Concentrix", "31549"), ("TaskUs", "350702"), ("Alorica", "17814"),
    ("Foundever", "11480"), ("Sutherland", "234815"),
    ("Sutherland-Global-Services", "25705"),
    ("Transcom-WorldWide", "30914"), ("SYKES", "5972"),
    ("TELUS-Digital", "2841163"), ("TELUS", "8006"),
    ("Genpact", "42613"), ("Modis", "18712"),
    ("Infosys", "7927"), ("Capgemini", "3803"), ("Deloitte", "2763"),
    ("EY", "2784"), ("KPMG", "2867"), ("PwC", "8450"), ("SAP", "10471"),
    ("Oracle", "1737"), ("Cisco", "1425"), ("Wipro", "9936"),
    ("NTT-DATA", "7649"), ("Tata-Consultancy-Services", "13461"),
    ("HCLTech", "553909"), ("DXC-Technology", "1603125"),
    ("HSBC", "3482"), ("DBS", "9444"),
]

# eids whose captured slugs are keyword variants — bare name is canonical
BARE_SLUG_EIDS = {"10471": "SAP", "1737": "Oracle", "2763": "Deloitte",
                  "3803": "Capgemini", "8014": "Cognizant",
                  "9936": "Wipro", "8450": "PwC", "2867": "KPMG"}


def main() -> int:
    targets: dict[str, dict] = {}
    order: list[str] = []

    def add(slug: str, eid: str, tier: str) -> None:
        if eid in targets:
            return
        targets[eid] = {"slug": slug, "eid": eid, "tier": tier}
        order.append(eid)

    # tier 1 — curated PH
    for slug, eid in CURATED_PH:
        add(slug, eid, "ph")
    # PAL: eid resolved from CDX discovery file
    cdx = {}
    p1 = STORAGE / "gd_ph_eids.json"
    if p1.exists():
        cdx = json.loads(p1.read_text(encoding="utf-8"))
        for v in cdx.values():
            if str(v["slug"]).lower() == "pal" and str(v["eid"]) != "4204596":
                add("PAL", str(v["eid"]), "ph")
                break

    # tier 2 — BPO / IT multinationals
    for slug, eid in CURATED_MULTI:
        add(slug, eid, "multi")

    # tier 3 — everything else named in the 2026 Wayback set
    p2 = STORAGE / "glassdoor_urls.json"
    groups: dict[str, list[str]] = {}
    if p2.exists():
        for r in json.loads(p2.read_text(encoding="utf-8")):
            m = PAT.search(r["url"])
            if not m or m.group(2) == "1196434":
                continue
            groups.setdefault(m.group(2), []).append(m.group(1))
    for eid, slugs in groups.items():
        if eid in targets:
            continue
        slug = min(slugs, key=len)
        add(BARE_SLUG_EIDS.get(eid, slug), eid, "other")

    targets_out = [targets[e] for e in order]
    out = STORAGE / "gd_live_targets.json"
    out.write_text(json.dumps(targets_out, indent=1), encoding="utf-8")

    tiers = {}
    for t in targets_out:
        tiers[t["tier"]] = tiers.get(t["tier"], 0) + 1
    print(f"total={len(targets_out)} tiers={tiers}")
    print("tier ph   :", [t["slug"] for t in targets_out if t["tier"] == "ph"])
    print("tier multi:", [t["slug"] for t in targets_out if t["tier"] == "multi"])
    print(f"SAVED -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
