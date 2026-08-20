"""晴红AI 提示词：系统角色、Few-shot 示例与消息组装。"""

from __future__ import annotations

import json

DEFAULT_SYSTEM_PROMPT = """你是电商发货地址解析助手，专门从非结构化收货文字中提取千牛发货所需字段。

输出规则（必须严格遵守）：
1. 只输出一个 JSON 对象，不要 markdown、不要解释、不要多余文字。
2. 字段固定为：name（收件人）、phone（11位手机号）、address（完整收货地址）。
3. 原文中的平台编号如 [9196] 必须原样保留在 name 和/或 address 中，不得删除或改写。
4. phone 只能是 11 位中国大陆手机号（1 开头），只输出数字，不含空格或符号。
5. address 必须完整，包含省市区及详细门牌，不得截断或省略。
6. 无法可靠识别某字段时，该字段留空字符串 ""，禁止编造信息。"""

FEW_SHOT_EXAMPLES: list[dict] = [
    {
        "user": (
            "请解析以下收货文字，严格返回 JSON："
            '{"name":"收件人(保留[四位数字]后缀)","phone":"11位手机号","address":"完整收货地址(保留[四位数字]后缀)"}\n'
            "原文：蔺玉泉[9196]15781066479天津市天津市河东区富民路街道月牙河南路与娄山道交叉路口往北约100米金月湾花园7号楼603[9196]"
        ),
        "assistant": {
            "name": "蔺玉泉[9196]",
            "phone": "15781066479",
            "address": "天津市天津市河东区富民路街道月牙河南路与娄山道交叉路口往北约100米金月湾花园7号楼603[9196]",
        },
    },
    {
        "user": (
            "请解析以下收货文字，严格返回 JSON："
            '{"name":"收件人(保留[四位数字]后缀)","phone":"11位手机号","address":"完整收货地址(保留[四位数字]后缀)"}\n'
            "原文：四川省广安市广安区 中桥街道四川省广安市广安区金安大道三段299号华冠城1701，漆洪兰，13541869970"
        ),
        "assistant": {
            "name": "漆洪兰",
            "phone": "13541869970",
            "address": "四川省广安市广安区 中桥街道四川省广安市广安区金安大道三段299号华冠城1701",
        },
    },
]


def build_user_prompt(text: str) -> str:
    return (
        "请解析以下收货文字，严格返回 JSON：\n"
        '{"name":"收件人(保留[四位数字]后缀)","phone":"11位手机号","address":"完整收货地址(保留[四位数字]后缀)"}\n'
        f"原文：{text.strip()}"
    )


def build_ai_messages(text: str, custom_system_prompt: str = "") -> list[dict]:
    """组装 system + few-shot + 当前用户输入。"""
    system = (custom_system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    messages: list[dict] = [{"role": "system", "content": system}]
    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example["user"]})
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(example["assistant"], ensure_ascii=False),
            }
        )
    messages.append({"role": "user", "content": build_user_prompt(text)})
    return messages
