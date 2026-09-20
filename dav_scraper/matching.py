from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Callable

ABBREVIATIONS = {
    "ctcp": "cong ty co phan",
    "c p": "co phan",
    "cp": "co phan",
    "cty": "cong ty",
    "d p": "duoc pham",
    "dp": "duoc pham",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")
    value = value.casefold().replace("đ", "d")
    value = re.sub(r"[_\-/.,;:()]+", " ", value)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _expand_abbreviations(value: str) -> str:
    tokens = value.split()
    expanded = []
    for token in tokens:
        expanded.extend(ABBREVIATIONS.get(token, token).split())
    return " ".join(expanded)


def build_variants(keywords: Iterable[str]) -> set[str]:
    variants = {normalize(k) for k in keywords if normalize(k)}
    variants |= {_expand_abbreviations(v) for v in variants}
    # Both the brand and legal-name forms are intentionally included.
    variants |= {
        "vinphaco", "vin phaco", "vinh phuc", "vinhphuc",
        "cong ty co phan duoc pham vinh phuc",
        "cong ty co phan duoc pham vin phuc",
        "ctcp duoc pham vinh phuc",
        "cty cp duoc pham vinh phuc",
    }
    return {re.sub(r"\s+", " ", v).strip() for v in variants if v}


def build_matcher(keywords: Iterable[str]) -> Callable[[str], bool]:
    variants = build_variants(keywords)
    compact = {v.replace(" ", "") for v in variants if len(v.replace(" ", "")) >= 5}

    def matches(value: str) -> bool:
        text = normalize(value)
        if any(v in text for v in variants):
            return True
        text_compact = text.replace(" ", "")
        return any(v in text_compact for v in compact)

    return matches
