"""Command-line entry point for the DAV public-portal collector."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from time import monotonic

from dav_scraper.config import DEFAULT_KEYWORDS, SITE_URL
from dav_scraper.crawler import DavCrawler
from dav_scraper.exporter import export_xlsx, write_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Vinphaco declarations from the DAV portal.")
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS)
    parser.add_argument("--output", default="output/vinphaco_results.xlsx")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--min-delay", type=float, default=2.0, help="Minimum delay between requests in seconds.")
    parser.add_argument("--max-delay", type=float, default=5.0, help="Maximum delay between requests in seconds.")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")
    output = Path(args.output)
    started = monotonic()
    crawler = DavCrawler(
        url=SITE_URL,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        retries=args.retries,
        timeout=args.timeout,
    )
    result = crawler.collect(args.keywords, max_pages=args.max_pages)
    elapsed = monotonic() - started
    export_xlsx(result.records, output)
    write_summary(output.parent, result, args.keywords, elapsed)
    logging.info("Completed: %s matching records; pages=%s; status=%s", len(result.records), result.pages_read, result.status)
    logging.info("Excel: %s", output)
    logging.info("Summary: %s", output.parent / "summary.json")
    return 0 if result.status in {"success", "no_records_found"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
