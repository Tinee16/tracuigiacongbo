from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import CrawlResult


def export_xlsx(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in records:
        row = {f"column_{i + 1}": value for i, value in enumerate(record.get("cells", []))}
        row["page"] = record.get("page")
        row["row_text"] = record.get("row_text")
        rows.append(row)
    if not rows:
        rows = [{"page": None, "row_text": "No records found"}]
    pd.DataFrame(rows).to_excel(path, index=False)


def write_summary(directory: Path, result: CrawlResult, keywords: list[str], elapsed: float) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": result.status,
        "message": result.message,
        "records_found": len(result.records),
        "pages_read": result.pages_read,
        "elapsed_seconds": round(elapsed, 2),
        "keywords": keywords,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (directory / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
