"""手机号等字段校验。"""

from __future__ import annotations

import re

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


def validate_phone(phone: str) -> str:
    phone = (phone or "").strip()
    if not phone:
        return "手机号为空"
    digits = re.sub(r"\D", "", phone)
    if len(digits) != 11:
        return "手机号应为11位"
    if digits.startswith("1"):
        if not PHONE_RE.match(digits):
            return "手机号号段异常"
        return ""
    if digits.startswith("0"):
        return ""
    return "手机号应为11位"


def apply_phone_validation(results) -> None:
    for item in results:
        msg = validate_phone(item.phone)
        if msg and item.ok:
            item.error = msg
