from __future__ import annotations

from dataclasses import dataclass

SITE_URL = "https://dichvucong.dav.gov.vn/congbogiathuoc/index"
DEFAULT_KEYWORDS = [
    "Vinphaco",
    "Công ty cổ phần dược phẩm Vĩnh Phúc",
    "Cong ty co phan duoc pham Vinh Phuc",
    "CTCP Dược phẩm Vĩnh Phúc",
    "Cty CP Dược phẩm Vĩnh Phúc",
    "Công ty CP Dược phẩm Vĩnh Phúc",
]

@dataclass(frozen=True)
class CrawlResult:
    records: list[dict]
    pages_read: int
    status: str
    message: str = ""
