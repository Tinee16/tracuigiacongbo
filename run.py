from pathlib import Path
import json
import re
import sys
import time
import unicodedata
from typing import Iterable, List, Set

import pandas as pd
import requests
from bs4 import BeautifulSoup

SITE_URL = "https://dichvucong.dav.gov.vn/congbogiathuoc/index"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)


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
        cleaned = kw.strip()
        variants.add(cleaned)
        variants.add(cleaned.lower())
        variants.add(cleaned.upper())
        variants.add(cleaned.replace("_", " "))
        variants.add(cleaned.replace("-", " "))
        variants.add(unicode_normalize(cleaned))
        variants.add(re.sub(r"\s+", "", unicode_normalize(cleaned)))

        if "vinphaco" in unicode_normalize(cleaned):
            variants.update({"vinphaco", "vin phaco", "vin_phaco", "vin-phaco"})

        if "vinh phuc" in unicode_normalize(cleaned) or "vinhphuc" in unicode_normalize(cleaned):
            variants.update({
                "vinh phuc",
                "vinhphuc",
                "vinh_phuc",
                "vinh-phuc",
                "ctcp duoc pham vinh phuc",
                "công ty cổ phần dược phẩm vĩnh phúc",
                "cong ty co phan duoc pham vinh phuc",
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


def fetch_page(session: requests.Session, page_number: int) -> str:
    response = session.get(SITE_URL, params={"page": page_number}, timeout=30)
    if response.status_code in (403, 429):
        raise RuntimeError(f"Access blocked by site: HTTP {response.status_code}")
    response.raise_for_status()
    return response.text


def parse_table_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for tr in soup.select("table tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append({"cells": cells})
    return rows


def row_matches_keyword(row_cells: Iterable[str], keyword_variants: List[str]) -> bool:
    blob = " ".join(row_cells).lower()
    normalized_blob = unicode_normalize(blob)
    for variant in keyword_variants:
        variant_norm = unicode_normalize(variant)
        if variant_norm and variant_norm in normalized_blob:
            return True
    return False


def crawl_keywords(keywords: List[str], max_pages: int = 20, delay_seconds: float = 1.5) -> List[dict]:
    session = build_session()
    keyword_variants = build_keyword_variants(*keywords)
    matches: List[dict] = []
    seen: Set[str] = set()

    for page_number in range(1, max_pages + 1):
        try:
            html = fetch_page(session, page_number)
            rows = parse_table_rows(html)
            page_matches = 0
            for row in rows:
                cells = row["cells"]
                if row_matches_keyword(cells, keyword_variants):
                    text = " | ".join(cells)
                    if text not in seen:
                        seen.add(text)
                        matches.append({
                            "page": page_number,
                            "text": text,
                            "raw_row": cells,
                        })
                        page_matches += 1

            soup = BeautifulSoup(html, "lxml")
            has_next = False
            for a in soup.select("a, button"):
                label = a.get_text(" ", strip=True).lower()
                if any(token in label for token in ["next", "tiếp", "sau", "trang", "page"]):
                    has_next = True
                    break
            if not has_next and page_matches == 0 and page_number > 1:
                break
            if not has_next and page_number >= 1:
                break

        except requests.exceptions.RequestException as exc:
            print(f"Request failure on page {page_number}: {exc}", file=sys.stderr)
            break
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            break

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return matches


def export_to_excel(records: List[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in records:
        rows.append({
            "page": record.get("page"),
            "row_text": record.get("text"),
            "raw_row": " | ".join(record.get("raw_row", [])),
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
