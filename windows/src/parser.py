"""收货地址解析：规则引擎 + 可选 AI 兜底。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

PHONE_RE = re.compile(r"1[3-9]\d{9}")
PHONE_VIRTUAL_RE = re.compile(r"0\d{10}")
ORDER_TAG_RE = re.compile(r"\[(\d{4})\]")
CHINESE_COMMA = "，"
ADDR_MARKERS = ("省", "市", "区", "县", "镇", "乡", "街道", "路", "号", "村", "栋", "室", "单元", "小区", "幢")
VIRTUAL_SUFFIX_RE = re.compile(r"[\(（][^)）]*虚拟[^)）]*[\)）]", re.I)


def extract_phone(text: str) -> str:
    """提取 11 位手机号；支持 1 开头实号与 0 开头虚拟号（快手等）。"""
    text = text or ""
    m = PHONE_RE.search(text)
    if m:
        return m.group()
    m = PHONE_VIRTUAL_RE.search(text)
    if m:
        return m.group()
    return ""


def _looks_like_name(line: str) -> bool:
    line = (line or "").strip()
    if not line or len(line) > 30:
        return False
    if any(m in line for m in ADDR_MARKERS[:5]):
        return False
    if extract_phone(line) and len(line) > 15:
        return False
    if 1 <= len(line) <= 4:
        return True
    return len(line) <= 20


def _looks_like_address(line: str) -> bool:
    line = (line or "").strip()
    if not line:
        return False
    return any(m in line for m in ADDR_MARKERS)


def _is_phone_only_line(line: str) -> bool:
    """判断是否为「单独一行手机号」（多行格式中间行）。"""
    phone = extract_phone(line)
    if not phone:
        return False
    rest = line.replace(phone, "")
    rest = VIRTUAL_SUFFIX_RE.sub("", rest)
    rest = re.sub(r"[\s\-—]+", "", rest)
    return len(rest) <= 2


@dataclass
class ParseResult:
    name: str = ""
    phone: str = ""
    address: str = ""
    order_no: str = ""
    product_info: str = ""
    spec_info: str = ""
    quantity: str = ""
    weight: str = ""
    remark: str = ""
    source: str = "rule"
    confidence: float = 1.0
    error: str = ""
    raw: str = ""
    hit_keywords: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.name and self.phone and self.address and not self.error)


def extract_order_tags(text: str) -> list[str]:
    return ORDER_TAG_RE.findall(text)


def pick_order_no(text: str) -> str:
    tags = extract_order_tags(text)
    if tags:
        return tags[0]
    suffix = re.search(r"1[3-9]\d{9}[-－](\d{4})", text or "")
    if suffix:
        return suffix.group(1)
    return ""


def _normalize(text: str) -> str:
    text = text.strip()
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_address(text: str) -> str:
    """收货地址：全角空格转半角，连续空白合并为单个空格。"""
    text = (text or "").strip()
    text = text.replace("\u3000", " ")
    return re.sub(r" +", " ", text)


def _finalize(result: ParseResult) -> ParseResult:
    if result.address:
        result.address = _normalize_address(result.address)
    return result


def parse_by_multiline(text: str) -> ParseResult | None:
    """多行式：姓名 / 手机号 / 地址 分行（含快手虚拟号、带[编号]）。"""
    raw = text.strip()
    if not raw:
        return None

    lines = [ln.strip() for ln in raw.replace("\r\n", "\n").split("\n") if ln.strip()]
    if len(lines) < 2:
        return None

    phone_idx = -1
    phone = ""
    for i, ln in enumerate(lines):
        p = extract_phone(ln)
        if p and (_is_phone_only_line(ln) or (len(lines) <= 4 and i > 0)):
            phone_idx = i
            phone = p
            break

    if phone_idx < 0:
        return None

    name = ""
    if phone_idx > 0 and _looks_like_name(lines[phone_idx - 1]):
        name = lines[phone_idx - 1]

    addr_parts = lines[phone_idx + 1 :]
    if not addr_parts and phone_idx > 1:
        addr_parts = [ln for j, ln in enumerate(lines) if j != phone_idx and ln != name]
    address = "".join(addr_parts) if addr_parts else ""

    if not name and not address:
        return None
    if not address and name:
        return None

    if not name and phone_idx == 0 and len(lines) >= 2:
        return None

    full_text = "\n".join(lines)
    return ParseResult(
        name=name,
        phone=phone,
        address=address,
        order_no=pick_order_no(full_text),
        source="rule-multiline",
        confidence=0.93,
        raw=raw,
    )


def parse_by_phone_anchor(text: str) -> ParseResult | None:
    """紧凑式：姓名[编号] + 手机 + 地址[编号]"""
    text = _normalize(text)
    match = PHONE_RE.search(text)
    if not match:
        match = PHONE_VIRTUAL_RE.search(text)
    if not match:
        return None

    phone = match.group()
    left = text[: match.start()].strip()
    right = text[match.end() :].strip()

    if not left or not right:
        return None

    # 左侧像姓名（较短，无省市区关键词）
    addr_markers = ("省", "市", "区", "县", "镇", "乡", "街道", "路", "号", "村", "栋")
    left_is_name = len(left) <= 30 and not any(m in left for m in addr_markers[:4])
    if not left_is_name:
        return None

    return ParseResult(
        name=left,
        phone=phone,
        address=right,
        order_no=pick_order_no(text),
        source="rule-compact",
        confidence=0.95,
        raw=text,
    )


def parse_by_comma_forward(text: str) -> ParseResult | None:
    """逗号正序：姓名，手机号(-四位后缀)，地址。如：贺，15782115734-0319，上海市..."""
    raw = text.strip()
    if "，" not in raw and "," not in raw:
        return None

    parts = [p.strip() for p in re.split(r"[，,]", raw) if p.strip()]
    if len(parts) < 3:
        return None

    name = parts[0]
    phone_part = parts[1]
    address = "，".join(parts[2:])

    if not _looks_like_name(name):
        return None
    if not address or (_looks_like_name(address) and not _looks_like_address(address)):
        return None
    if not _looks_like_address(address) and len(address) < 6:
        return None

    phone = extract_phone(phone_part)
    if not phone:
        return None

    return ParseResult(
        name=name,
        phone=phone,
        address=address,
        order_no=pick_order_no(raw),
        source="rule-comma-fwd",
        confidence=0.94,
        raw=raw,
    )


def parse_by_comma_reverse(text: str) -> ParseResult | None:
    """逗号倒序：地址，姓名，手机"""
    text = _normalize(text)
    if CHINESE_COMMA not in text:
        return None

    match = PHONE_RE.search(text)
    if not match:
        match = PHONE_VIRTUAL_RE.search(text)
    if not match:
        return None

    phone = match.group()
    before_phone = text[: match.start()].rstrip("，,;； ")
    parts = [p.strip() for p in before_phone.split(CHINESE_COMMA) if p.strip()]
    if len(parts) < 2:
        return None

    name = parts[-1]
    address = CHINESE_COMMA.join(parts[:-1])

    if len(name) > 20 or any(m in name for m in ("省", "市", "区", "县", "街道", "路", "号")):
        return None

    return ParseResult(
        name=name,
        phone=phone,
        address=address,
        order_no=pick_order_no(text),
        source="rule-comma",
        confidence=0.92,
        raw=text,
    )


def parse_by_phone_split(text: str) -> ParseResult | None:
    """通用：以手机为锚点，尝试推断姓名与地址。"""
    text = _normalize(text)
    match = PHONE_RE.search(text)
    if not match:
        match = PHONE_VIRTUAL_RE.search(text)
    if not match:
        return None

    phone = match.group()
    left = text[: match.start()].strip("，,;； ")
    right = text[match.end() :].strip("，,;； ")

    addr_markers = ("省", "市", "区", "县", "镇", "乡", "街道", "路", "号", "村", "栋", "室", "单元")
    left_score = sum(1 for m in addr_markers if m in left)
    right_score = sum(1 for m in addr_markers if m in right)

    if left_score >= right_score and right:
        name, address = left, right
    elif right_score > left_score and left:
        name, address = right, left
    else:
        return None

    if not name or not address:
        return None

    return ParseResult(
        name=name,
        phone=phone,
        address=address,
        order_no=pick_order_no(text),
        source="rule-anchor",
        confidence=0.75,
        raw=text,
    )


def parse_with_rules(text: str) -> ParseResult:
    text = text.strip()
    if not text:
        return ParseResult(error="空行", raw=text)

    for fn in (
        parse_by_multiline,
        parse_by_comma_forward,
        parse_by_comma_reverse,
        parse_by_phone_anchor,
        parse_by_phone_split,
    ):
        result = fn(text)
        if result and result.ok:
            return _finalize(result)

    return ParseResult(
        error="规则无法识别，可尝试 AI 解析",
        raw=text,
        confidence=0.0,
    )


def parse_with_ai(text: str, ai_client, custom_system_prompt: str = "") -> ParseResult:
    if not ai_client or not ai_client.available:
        return ParseResult(error="AI 未配置", raw=text, confidence=0.0)

    try:
        from .ai_prompts import build_ai_messages

        messages = build_ai_messages(text, custom_system_prompt)
        content = ai_client.chat_messages(messages)
        data = json.loads(content)
        result = ParseResult(
            name=str(data.get("name", "")).strip(),
            phone=str(data.get("phone", "")).strip(),
            address=str(data.get("address", "")).strip(),
            order_no=pick_order_no(text) or pick_order_no(str(data.get("name", "")) + str(data.get("address", ""))),
            source="ai",
            confidence=0.85,
            raw=text,
        )
        if not PHONE_RE.fullmatch(result.phone):
            extracted = extract_phone(result.phone)
            result.phone = extracted or result.phone
        if not result.ok:
            result.error = "AI 返回字段不完整"
        return _finalize(result)
    except Exception as exc:
        from .ai_client import QinghongAIError

        if isinstance(exc, QinghongAIError):
            return ParseResult(error=str(exc), raw=text, confidence=0.0)
        return ParseResult(error=f"AI 解析失败: {exc}", raw=text, confidence=0.0)


def parse_one(
    text: str,
    ai_client=None,
    use_ai: bool = True,
    custom_system_prompt: str = "",
) -> ParseResult:
    result = parse_with_rules(text)
    if result.ok:
        return result
    if use_ai and ai_client:
        ai_result = parse_with_ai(text, ai_client, custom_system_prompt=custom_system_prompt)
        if ai_result.ok:
            return ai_result
        if not result.error:
            result.error = ai_result.error
    return result


def _group_lines_by_phone(lines: list[str]) -> list[str]:
    """将多行文本按「手机号行」分组为多条记录。"""
    if not lines:
        return []

    phone_idxs = [i for i, ln in enumerate(lines) if extract_phone(ln)]
    if not phone_idxs:
        return ["\n".join(lines)] if lines else []

    records: list[str] = []
    for pi, pidx in enumerate(phone_idxs):
        if _is_phone_only_line(lines[pidx]):
            start = pidx - 1 if pidx > 0 and _looks_like_name(lines[pidx - 1]) else pidx
            if pi + 1 < len(phone_idxs):
                next_p = phone_idxs[pi + 1]
                end = next_p - 1 if next_p > 0 and _looks_like_name(lines[next_p - 1]) else next_p
            else:
                end = len(lines)
            records.append("\n".join(lines[start:end]))
        else:
            records.append(lines[pidx])
    return records


def _nonempty_lines(block: str) -> list[str]:
    return [ln.strip() for ln in block.replace("\r\n", "\n").split("\n") if ln.strip()]


def _merge_fragment_blocks(blocks: list[str]) -> list[str]:
    """合并京东等粘贴时「姓名」与「手机+地址」被空行拆开的碎片块。

    典型：
        陈禄寿
        <空行>
        13594567686
        重庆市...
    """
    merged: list[str] = []
    i = 0
    while i < len(blocks):
        lines = _nonempty_lines(blocks[i])
        has_phone = any(extract_phone(ln) for ln in lines)
        if (
            not has_phone
            and len(lines) == 1
            and _looks_like_name(lines[0])
            and i + 1 < len(blocks)
        ):
            next_lines = _nonempty_lines(blocks[i + 1])
            if next_lines and extract_phone(next_lines[0]) and (
                _is_phone_only_line(next_lines[0]) or len(next_lines[0]) <= 20
            ):
                merged.append("\n".join(lines + next_lines))
                i += 2
                continue
        merged.append(blocks[i])
        i += 1
    return merged


def split_records(raw: str, separator: str = "auto", custom_sep: str = "") -> list[str]:
    """多条记录分隔。separator: auto | blank_line | newline | semicolon | custom"""
    raw = raw.replace("\r\n", "\n").strip()
    if not raw:
        return []

    if separator == "newline":
        return [ln.strip() for ln in raw.split("\n") if ln.strip()]
    if separator == "semicolon":
        return [p.strip() for p in re.split(r"[;；]", raw) if p.strip()]
    if separator == "custom" and custom_sep:
        return [p.strip() for p in raw.split(custom_sep) if p.strip()]

    # auto / blank_line：先按空行切块，再合并「姓名 ↔ 手机」被空行拆开的碎片
    blocks = re.split(r"\n\s*\n", raw)
    if separator == "auto" and len(blocks) == 1:
        lines = _nonempty_lines(raw)
        if not lines:
            return []
        phone_only_count = sum(1 for ln in lines if _is_phone_only_line(ln))
        if phone_only_count >= 1 and len(lines) >= 3:
            return _group_lines_by_phone(lines)
        return lines

    blocks = _merge_fragment_blocks(blocks)

    records: list[str] = []
    for block in blocks:
        lines = _nonempty_lines(block)
        if not lines:
            continue
        if len(lines) == 1:
            records.append(lines[0])
        elif sum(1 for ln in lines if _is_phone_only_line(ln)) >= 1:
            records.extend(_group_lines_by_phone(lines))
        else:
            records.extend(lines)
    return records


def parse_batch(
    raw: str,
    ai_client=None,
    use_ai: bool = True,
    separator: str = "auto",
    custom_sep: str = "",
    custom_system_prompt: str = "",
) -> list[ParseResult]:
    items = split_records(raw, separator=separator, custom_sep=custom_sep)
    return [
        parse_one(item, ai_client=ai_client, use_ai=use_ai, custom_system_prompt=custom_system_prompt)
        for item in items
    ]
