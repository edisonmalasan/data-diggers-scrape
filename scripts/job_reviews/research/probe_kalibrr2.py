"""Inspect Kalibrr company-page __NEXT_DATA__ for the review object structure.

Dumps the props of one real company page (globant) and prints any keys
matching review/rating/pros/cons, plus a sample review object, so a
scraper can be written against the exact schema.
"""
from __future__ import annotations

import json
import re

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

URL = "https://www.kalibrr.com/home/company/globant"
r = requests.get(URL, headers=H, timeout=45)
print(f"status={r.status_code} len={len(r.text)} final={r.url}")

m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.S)
assert m, "no NEXT_DATA"
data = json.loads(m.group(1))


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            kl = k.lower()
            if any(t in kl for t in ("review", "rating", "pros", "cons", "testimonial")):
                kind = type(v).__name__
                n = len(v) if isinstance(v, (list, dict, str)) else v
                print(f"HIT {path}.{k} ({kind}) n={n}")
            walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node[:3]):
            walk(v, f"{path}[{i}]")


walk(data)

# Heuristic: find the deepest dict/list containing both 'pros' and 'cons' keys
found = []


def find_reviews(node, path=""):
    if isinstance(node, dict):
        keys = {k.lower() for k in node}
        if "pros" in keys and "cons" in keys:
            found.append((path, node))
        for k, v in node.items():
            find_reviews(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            find_reviews(v, f"{path}[{i}]")


find_reviews(data)
print(f"\n{len(found)} dicts with pros+cons")
for path, obj in found[:2]:
    print(f"\n--- {path} ---")
    print(json.dumps(obj, indent=1, ensure_ascii=False)[:2500])

# page props top-level keys of interest
pp = data.get("props", {}).get("pageProps", {})
print("\npageProps keys:", list(pp.keys())[:40])
