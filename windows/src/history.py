"""解析历史记录（最近 5 批）。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import app_dir
from .parser import ParseResult

MAX_HISTORY = 5


def history_path() -> Path:
    return app_dir() / "history.json"


def _serialize_results(results: list[ParseResult]) -> list[dict]:
    return [
        {
            "name": r.name,
            "phone": r.phone,
            "address": r.address,
            "order_no": r.order_no,
            "product_info": r.product_info,
            "spec_info": r.spec_info,
            "quantity": r.quantity,
            "weight": r.weight,
            "remark": r.remark,
            "source": r.source,
            "error": r.error,
            "raw": r.raw,
            "hit_keywords": r.hit_keywords,
        }
        for r in results
    ]


def _deserialize_results(data: list[dict]) -> list[ParseResult]:
    out: list[ParseResult] = []
    for item in data:
        out.append(
            ParseResult(
                name=item.get("name", ""),
                phone=item.get("phone", ""),
                address=item.get("address", ""),
                order_no=item.get("order_no", ""),
                product_info=item.get("product_info", ""),
                spec_info=item.get("spec_info", ""),
                quantity=item.get("quantity", ""),
                weight=item.get("weight", ""),
                remark=item.get("remark", ""),
                source=item.get("source", "rule"),
                error=item.get("error", ""),
                raw=item.get("raw", ""),
                hit_keywords=item.get("hit_keywords", []),
            )
        )
    return out


def load_history() -> list[dict]:
    path = history_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_history_entry(raw: str, results: list[ParseResult]) -> None:
    entries = load_history()
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(results),
        "raw": raw,
        "results": _serialize_results(results),
    }
    entries.insert(0, entry)
    entries = entries[:MAX_HISTORY]
    with history_path().open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def get_history_entry(index: int) -> tuple[str, list[ParseResult]] | None:
    entries = load_history()
    if index < 0 or index >= len(entries):
        return None
    item = entries[index]
    return item.get("raw", ""), _deserialize_results(item.get("results", []))
