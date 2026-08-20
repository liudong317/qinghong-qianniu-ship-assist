"""关键词匹配与整行标红判定。"""

from __future__ import annotations

import re

from .parser import ParseResult

DEFAULT_KEYWORDS = ["驿站", "工商局", "质检局"]
DEFAULT_KEYWORD_SCAN = {
    "name": True,
    "address": True,
    "phone": False,
    "remark": False,
}
FIELD_MAP = {
    "name": "name",
    "address": "address",
    "phone": "phone",
    "remark": "remark",
}


def get_scan_fields(scan_config: dict | None) -> tuple[str, ...]:
    cfg = {**DEFAULT_KEYWORD_SCAN, **(scan_config or {})}
    return tuple(field for key, field in FIELD_MAP.items() if cfg.get(key, False))


def _match_keyword(kw: str, text: str, mode: str) -> bool:
    kw = kw.strip()
    if not kw or not text:
        return False
    if mode == "regex":
        try:
            return re.search(kw, text) is not None
        except re.error:
            return kw in text
    return kw in text


def scan_keywords(
    result: ParseResult,
    keywords: list[str],
    scan_config: dict | None = None,
    mode: str = "contains",
) -> list[str]:
    if not keywords:
        return []

    fields = get_scan_fields(scan_config)
    haystack = " ".join(getattr(result, field, "") or "" for field in fields)
    hits: list[str] = []
    for kw in keywords:
        if _match_keyword(kw, haystack, mode) and kw not in hits:
            hits.append(kw)
    return hits


def apply_keyword_hits(
    results: list[ParseResult],
    keywords: list[str],
    scan_config: dict | None = None,
    mode: str = "contains",
) -> None:
    for item in results:
        item.hit_keywords = scan_keywords(item, keywords, scan_config, mode)
