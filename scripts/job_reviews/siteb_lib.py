"""Shared polite-fetch helpers for the Site-B batch (fishbowl/blind/layoff/...).

NOT a scraper target itself — imported by probe_b*.py scripts.
Gates/regex/ids are imported from scrape_jobstreet.py (never edited).
"""
from __future__ import annotations

import random
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class StopSite(Exception):
    """Circuit breaker tripped or request budget exhausted."""


class Fetcher:
    """Polite GET/HEAD: 2-3s delay, exp backoff capped 60s on 403/429/5xx,
    circuit breaker after 8 consecutive failures, ~600 request cap per site."""

    def __init__(self, site: str, max_requests: int = 600,
                 delay: float = 2.5, max_consec: int = 8):
        self.site = site
        self.sess = requests.Session()
        self.sess.headers.update({
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.n = 0
        self.max = max_requests
        self.delay = delay
        self.consec = 0
        self.max_consec = max_consec
        self.log_path = STORAGE / f"siteb_{site}.log"

    def _log(self, msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def _sleep(self) -> None:
        time.sleep(self.delay + random.uniform(0.0, 0.5))

    def _budget(self) -> None:
        if self.n >= self.max:
            raise StopSite(f"{self.site}: request budget {self.max} reached")
        if self.consec >= self.max_consec:
            raise StopSite(f"{self.site}: circuit breaker after {self.max_consec} consecutive failures")

    def get(self, url: str, timeout: int = 30, allow: str = "text/html,application/json,text/plain,*/*",
            stream_to: Path | None = None) -> requests.Response:
        self._budget()
        attempt = 0
        while True:
            self._budget()
            self.n += 1
            try:
                r = self.sess.get(url, timeout=timeout, allow_redirects=True, headers={"Accept": allow})
            except requests.RequestException as e:
                self.consec += 1
                self._log(f"ERR {type(e).__name__} {e} :: {url}")
                attempt += 1
                if attempt > 4 or self.consec >= self.max_consec:
                    raise
                self._zz(attempt)
                continue
            if r.status_code in (403, 429) or 500 <= r.status_code < 600:
                self.consec += 1
                self._log(f"HTTP {r.status_code} :: {url} (consec={self.consec})")
                attempt += 1
                if attempt > 5 or self.consec >= self.max_consec:
                    self._sleep()
                    return r
                self._zz(attempt)
                continue
            self.consec = 0
            self._log(f"HTTP {r.status_code} len={len(r.content)} :: {url}")
            if stream_to is not None:
                stream_to.write_bytes(r.content)
            self._sleep()
            return r

    def head(self, url: str, timeout: int = 30) -> requests.Response:
        self._budget()
        attempt = 0
        while True:
            self._budget()
            self.n += 1
            try:
                r = self.sess.head(url, timeout=timeout, allow_redirects=True)
            except requests.RequestException as e:
                self.consec += 1
                self._log(f"HEAD ERR {type(e).__name__} :: {url}")
                attempt += 1
                if attempt > 4 or self.consec >= self.max_consec:
                    raise
                self._zz(attempt)
                continue
            if r.status_code in (403, 429) or 500 <= r.status_code < 600:
                self.consec += 1
                self._log(f"HEAD {r.status_code} :: {url}")
                attempt += 1
                if attempt > 5 or self.consec >= self.max_consec:
                    self._sleep()
                    return r
                self._zz(attempt)
                continue
            self.consec = 0
            self._log(f"HEAD {r.status_code} ct={r.headers.get('Content-Type','')} :: {url}")
            self._sleep()
            return r

    def _zz(self, attempt: int) -> None:
        backoff = min(60.0, 2.0 ** attempt)
        self._log(f"backoff {backoff:.0f}s (attempt {attempt})")
        time.sleep(backoff)

    @property
    def stats(self) -> dict:
        return {"site": self.site, "requests": self.n, "consec_failures": self.consec}
