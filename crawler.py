from __future__ import annotations

import json
from pathlib import Path
from time import time

from crawler import crawl_keywords, export_to_excel, write_summary


DEFAULT_KEYWORDS = [
    "Vinphaco",
    "Công ty cổ phần dược phẩm Vĩnh Phúc",
    "Cong ty co phan duoc pham Vinh Phuc",
    "CTCP dược phẩm Vĩnh Phúc",
    "Cty CP duoc pham Vinh Phuc",
]


def main() -> None:
    output_dir = Path("output")
    output_file = output_dir / "vinphaco_results.xlsx"
    output_dir.mkdir(exist_ok=True, parents=True)

    print("Starting data extraction for Vinphaco-related declarations...")
    start = time()
    results = crawl_keywords(DEFAULT_KEYWORDS, max_pages=20, delay_seconds=1.5)
    elapsed = time() - start

    export_to_excel(results, output_file)
    write_summary(output_dir, results, DEFAULT_KEYWORDS, elapsed)

    print(f"Matched rows: {len(results)}")
    print(f"Excel file: {output_file}")
    print(f"Summary file: {output_dir / 'summary.json'}")

    if not results:
        print("No records matched. Check if the site blocked automated requests or changed the page structure.")


if __name__ == "__main__":
    main()
