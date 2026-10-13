"""Parse Blind reviews from Next.js flight payloads (shared by probe scripts)."""
from __future__ import annotations

import json
import re

FLIGHT_RE = re.compile(r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\]', re.S)
REVIEW_START = re.compile(r'\{"id":\d+,"isFeatured"')


def flight_strings(html: str) -> list[str]:
    out = []
    for m in FLIGHT_RE.finditer(html):
        try:
            out.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            continue
    return out


def _objects(s: str, start: int) -> dict | None:
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[start:i + 1])
                    except json.JSONDecodeError:
                        return None
    return None


def extract_reviews(html: str) -> list[dict]:
    seen: set[int] = set()
    out: list[dict] = []
    for s in flight_strings(html):
        for m in REVIEW_START.finditer(s):
            obj = _objects(s, m.start())
            if not obj or "memberLocation" not in obj or "jobgroup" not in obj:
                continue
            rid = obj.get("id")
            if rid in seen:
                continue
            seen.add(rid)
            out.append(obj)
    return out


def extract_total(html: str) -> int:
    for s in flight_strings(html):
        m = re.search(r'"total":(\d+)', s)
        if m:
            return int(m.group(1))
    m = re.search(r'\\"total\\":(\d+)', html)
    return int(m.group(1)) if m else -1


def extract_facets(html: str, key: str) -> list[dict]:
    for s in flight_strings(html):
        i = s.find('"' + key + '":[')
        if i < 0:
            continue
        j = s.index("[", i)
        depth = 0
        in_str = False
        esc = False
        for k in range(j, len(s)):
            c = s[k]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "[":
                    depth += 1
                elif c == "]":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(s[j:k + 1])
                        except json.JSONDecodeError:
                            return []
        return []
    return []


if __name__ == "__main__":
    from pathlib import Path
    p = Path(__file__).resolve().parent / ".storage"
    for name in ("blind_company_google_rev.html", "blind_co_Accenture.html"):
        h = (p / name).read_text(encoding="utf-8", errors="replace")
        rs = extract_reviews(h)
        print(f"## {name}: reviews={len(rs)} total={extract_total(h)}")
        for r in rs[:5]:
            print("   ", r.get("companyName"), "|", r.get("jobgroup"), "|",
                  r.get("memberLocation"), "|", r.get("memberLocationCountryIsoCode"),
                  "|", r.get("createdAt"), "| pros=", (r.get("pros") or "")[:40])
        ph = [r for r in rs if r.get("memberLocationCountryIsoCode") == "PH"]
        print("    PH rows on this page:", len(ph))
