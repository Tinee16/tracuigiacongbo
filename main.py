from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, List, Set
import unicodedata

import pandas as pd
import requests
from bs4 import BeautifulSoup

SITE_URL = "https://dichvucong.dav.gov.vn/congbogiathuoc/index"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)

DEFAULT_KEYWORDS = [
    "Vinphaco",
    "Công ty cổ phần dược phẩm Vĩnh Phúc",
    "Cong ty co phan duoc pham Vinh Phuc",
    "CTCP dược phẩm Vĩnh Phúc",
    "Cty CP duoc pham Vinh Phuc",
]


def unicode_normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower()
    value = re.sub(r"[_\-\s]+", " ", value)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def build_keyword_variants(*raw_keywords: str) -> List[str]:
    variants: Set[str] = set()
    for kw in raw_keywords:
        if not kw or not kw.strip():
            continue
        variants.add(kw.strip())
        variants.add(kw.strip().lower())
        variants.add(kw.strip().upper())
        variants.add(kw.strip().replace("_", " "))
        variants.add(kw.strip().replace("-", " "))
        variants.add(kw.strip().replace("  ", " "))
        variants.add(unicode_normalize(kw))

        compact = re.sub(r"\s+", "", unicode_normalize(kw))
        variants.add(compact)

        # common shorthand variants for company name 
        if "vinphaco" in unicode_normalize(kw):
            variants.update({
                "vinphaco",
                "vin phaco",
                "vin_phaco",
                "vin-phaco",
            })
        if "vinh phuc" in unicode_normalize(kw) or "vinhphuc" in unicode_normalize(kw):
            variants.update({
                "vinh phuc",
                "vinhphuc",
                "vinh_phuc",
                "vinh-phuc",
                "ctcp duoc pham vinh phuc",
                "công ty cổ phần dược phẩm vĩnh phúc",
                "cong ty co phan duoc pham vinh phuc",
                "công ty cphđp vĩnh phúc",
            })
    return sorted(v for v in variants if v)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Upgrade-Insecure-Requests": "1",
        "Referer": SITE_URL,
    })
    return session


def fetch_html(session: requests.Session, url: str, timeout: int = 25) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_table_rows(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for tr in soup.select("table tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"]) ]
        if not cells:
            continue
        if len(cells) >= 2:
            rows.append({"cells": cells})
    return rows


def row_matches_keyword(row_cells: Iterable[str], keyword_variants: List[str]) -> bool:
    text_blob = " ".join(row_cells).lower()
    normalized_blob = unicode_normalize(text_blob)
    for variant in keyword_variants:
        variant_norm = unicode_normalize(variant)
        if variant_norm and variant_norm in normalized_blob:
            return True
    return False


def page_to_records(session: requests.Session, page_number: int = 1, keyword_variants: List[str] | None = None) -> tuple[list[dict], bool]:
    keyword_variants = keyword_variants or []
    params = {"page": page_number}
    response = session.get(SITE_URL, params=params, timeout=30)
    if response.status_code in (403, 429):
        raise RuntimeError(f"Access blocked by site: HTTP {response.status_code}")
    response.raise_for_status()
    html = response.text
    rows = parse_table_rows(html)
    matches = []
    for row in rows:
        cells = row["cells"]
        if row_matches_keyword(cells, keyword_variants):
            matches.append({
                "page": page_number,
                "raw_row": cells,
                "text": " | ".join(cells),
            })
    # check if there are page links/next control to keep crawling
    has_next_page = False
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select("a, button"):
        text = a.get_text(" ", strip=True).lower()
        if any(token in text for token in ["next", "tiếp", "sau", "page", "trang tiếp"]) and a.get("href"):
            has_next_page = True
            break
    return matches, has_next_page


def crawl_keywords(keywords: List[str], max_pages: int = 50, delay_seconds: float = 1.5) -> List[dict]:
    session = build_session()
    all_matches: List[dict] = []
    keyword_variants = build_keyword_variants(*keywords)

    for page_number in range(1, max_pages + 1):
        try:
            records, has_next = page_to_records(session, page_number, keyword_variants)
            if records:
                all_matches.extend(records)
            if not has_next:
                break
        except requests.exceptions.HTTPError as exc:
            print(f"HTTP error on page {page_number}: {exc}", file=sys.stderr)
            break
        except requests.exceptions.RequestException as exc:
            print(f"Request exception on page {page_number}: {exc}", file=sys.stderr)
            break
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            break

        if delay_seconds > 0:
            import time
            time.sleep(delay_seconds)

    # de-duplicate matches by text
    unique = {}
    for item in all_matches:
        unique[item["text"]] = item
    return list(unique.values())


def export_to_excel(records: List[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for r in records:
        rows.append({
            "page": r.get("page"),
            "row_text": r.get("text"),
            "raw_row": " | ".join(r.get("raw_row", [])),
        })

    dataframe = pd.DataFrame(rows)
    if dataframe.empty:
        dataframe = pd.DataFrame([
            {"page": None, "row_text": "No records found", "raw_row": "No records found"}
        ])

    dataframe.to_excel(output_path, index=False)


def write_summary(output_dir: Path, records: List[dict], keywords: List[str], elapsed_seconds: float):
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "keywords": keywords,
        "records_found": len(records),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "status": "success" if records else "no_records_found",
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
    with open(output_dir / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)


def parse_args():
    parser = argparse.ArgumentParser(description="Crawl data from DAV public portal for Vinphaco-related declarations.")
    parser.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS, help="List of search terms to match.")
    parser.add_argument("--output", default="output/vinphaco_results.xlsx", help="Output Excel path.")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum pages to crawl.")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between page requests.")
    return parser.parse_args()


def main():
    args = parse_args()
    output_path = Path(args.output)
    out_dir = output_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Searching for keywords: {args.keywords}")
    start = __import__("time").time()
    matches = crawl_keywords(args.keywords, max_pages=args.max_pages, delay_seconds=args.delay)
    elapsed = __import__("time").time() - start

    export_to_excel(matches, output_path)
    write_summary(out_dir, matches, args.keywords, elapsed)

    print(f"Done. Total matched records: {len(matches)}")
    print(f"Excel saved to: {output_path}")
    print(f"Summary saved to: {out_dir / 'summary.json'}")

    if not matches:
        print("Warning: no matching records were found. This may be because the portal blocks automated requests or the site structure changed.")


if __name__ == "__main__":
    main()
