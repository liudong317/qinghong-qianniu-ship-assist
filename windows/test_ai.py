"""AI 功能本地测试（密钥仅通过环境变量传入，不写入 config.json / exe）。"""

from __future__ import annotations

import os
import sys

from src.ai_client import QinghongAIClient
from src.parser import parse_with_ai

# 测试用环境变量（不在软件内硬编码）：
#   QH_AI_BASE_URL  QH_AI_API_KEY  QH_AI_MODEL
TEST_BASE_URL = os.environ.get("QH_AI_BASE_URL", "").strip()
TEST_API_KEY = os.environ.get("QH_AI_API_KEY", "").strip()
TEST_MODEL = os.environ.get("QH_AI_MODEL", "glm-5").strip()

# 规则难以识别的乱序样例
HARD_SAMPLE = (
    "收货人：赵六  联系电话13500001234  "
    "寄到-> 江苏省南京市鼓楼区湖南路街道丁家桥87号2单元301"
)


def main() -> int:
    if not TEST_BASE_URL or not TEST_API_KEY:
        print("请设置环境变量 QH_AI_BASE_URL 与 QH_AI_API_KEY 后再运行本脚本")
        return 1

    client = QinghongAIClient(TEST_BASE_URL, TEST_API_KEY, TEST_MODEL, timeout=60)
    print(f"=== 1. 连接测试 ({TEST_MODEL}) ===")
    ok, msg = client.test_connection()
    print(msg)
    if not ok:
        return 1

    print("\n=== 2. 地址解析测试（AI 兜底） ===")
    result = parse_with_ai(HARD_SAMPLE, client)
    print(f"来源: {result.source}")
    print(f"收件人: {result.name}")
    print(f"手机: {result.phone}")
    print(f"地址: {result.address}")
    print(f"状态: {'OK' if result.ok else 'FAIL'} | {result.error or '成功'}")

    if not result.ok:
        return 1
    if "13500001234" not in result.phone:
        print("手机号校验失败")
        return 1
    if "赵六" not in result.name:
        print("收件人校验失败")
        return 1
    if "南京" not in result.address:
        print("地址校验失败")
        return 1

    print("\n全部 AI 测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
