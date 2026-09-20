from __future__ import annotations

import logging
import random
import re
import time
from typing import Iterable
import unicodedata
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CrawlResult
from .matching import build_matcher

LOG = logging.getLogger(__name__)
NEXT_LABELS = ("next", "tiếp", "sau", "trang tiếp", "›", "»")
BLOCK_MARKERS = ("captcha", "access denied", "forbidden", "too many requests", "cloudflare")


class SiteBlocked(RuntimeError):
    """Raised when the server indicates that automation should stop."""


class DavCrawler:
    def __init__(self, url: str, min_delay: float = 2.0, max_delay: float = 5.0, retries: int = 3, timeout: float = 30.0):
        self.url = url
        self.min_delay = max(0.0, min_delay)
        self.max_delay = max(self.min_delay, max_delay)
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(total=retries, connect=retries, read=retries, backoff_factor=1.0,
                      status_forcelist=(500, 502, 503, 504), allowed_methods=frozenset({"GET"}),
                      raise_on_status=False)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update({
            "User-Agent": "tracuigiacongbo/1.0 (public-data research; contact repository owner)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "vi,en;q=0.8",
            "Referer": url,
        })
        self._last_request = 0.0

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def _get(self, url: str, params: dict | None = None) -> str:
        self._wait()
        response = self.session.get(url, params=params, timeout=self.timeout)
        self._last_request = time.monotonic()
        body = response.text[:20000].lower()
        if response.status_code in {401, 403, 429} or any(marker in body for marker in BLOCK_MARKERS):
            raise SiteBlocked(f"DAV requested that the client stop (HTTP {response.status_code}).")
        response.raise_for_status()
        return response.text

    @staticmethod
    def _rows(html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        result = []
        for table_index, table in enumerate(soup.select("table")):
            headers = [cell.get_text(" ", strip=True) for cell in table.select("thead th")]
            for tr in table.select("tbody tr") or table.select("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
                if cells and any(cells) and len(cells) > 1:
                    result.append({"table": table_index, "headers": headers, "cells": cells})
        return result

    def _next_url(self, html: str, current_url: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        current_page = None
        parsed = urlparse(current_url)
        if parse_qs(parsed.query).get("page"):
            current_page = parse_qs(parsed.query)["page"][0]
        for link in soup.select("a[href]"):
            label = link.get_text(" ", strip=True).lower()
            rel = " ".join(link.get("rel", [])).lower()
            aria = (link.get("aria-label") or "").lower()
            if any(token in f"{label} {rel} {aria}" for token in NEXT_LABELS):
                candidate = urljoin(current_url, link["href"])
                if candidate != current_url:
                    return candidate
        # Fallback only when the server exposes a page query parameter.
        if current_page and current_page.isdigit():
            return f"{self.url}?page={int(current_page) + 1}"
        return None

    def collect(self, keywords: Iterable[str], max_pages: int = 100) -> CrawlResult:
        matcher = build_matcher(keywords)
        records: list[dict] = []
        seen: set[str] = set()
        url = self.url
        pages_read = 0
        try:
            for page_number in range(1, max_pages + 1):
                html = self._get(url, {"page": page_number} if page_number == 1 else None)
                pages_read += 1
                rows = self._rows(html)
                for row in rows:
                    row_text = " | ".join(row["cells"])
                    if matcher(row_text):
                        key = re.sub(r"\s+", " ", row_text).strip().casefold()
                        if key not in seen:
                            seen.add(key)
                            records.append({"page": page_number, "headers": row["headers"], "cells": row["cells"], "row_text": row_text})
                next_url = self._next_url(html, url)
                if not next_url or next_url == url:
                    break
                url = next_url
            status = "success" if records else "no_records_found"
            return CrawlResult(records, pages_read, status)
        except SiteBlocked as exc:
            LOG.error("Collection stopped safely: %s", exc)
            return CrawlResult(records, pages_read, "blocked", str(exc))
        except requests.RequestException as exc:
            LOG.error("Collection stopped after a network error: %s", exc)
            return CrawlResult(records, pages_read, "network_error", str(exc))
