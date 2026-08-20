"""逗号正序样例：姓名，手机-后缀，地址。"""

from pathlib import Path

from src.parser import parse_batch, split_records
from src.validators import apply_phone_validation

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "测试样例-逗号正序.txt"

EXPECTED = [
    ("贺", "15782115734", "0319", "松江"),
    ("徐伟军", "15782132924", "2483", "余姚"),
    ("袁丽娜", "15782126657", "7363", "漯河"),
    ("孟素娟", "15784604672", "6379", "郾城"),
]


def main():
    raw = SAMPLES.read_text(encoding="utf-8").strip()
    records = split_records(raw)
    print(f"分隔得到 {len(records)} 条\n")
    assert len(records) == 4, f"期望4条，实际{len(records)}"

    results = parse_batch(raw, use_ai=False)
    apply_phone_validation(results)

    ok = 0
    for i, (r, (ename, ephone, eorder, ecity)) in enumerate(zip(results, EXPECTED), 1):
        status = "OK" if r.ok else "FAIL"
        if r.ok:
            ok += 1
        assert r.name == ename, f"[{i}] 姓名期望 {ename}，得 {r.name}"
        assert r.phone == ephone, f"[{i}] 手机期望 {ephone}，得 {r.phone}"
        assert r.order_no == eorder, f"[{i}] 后缀期望 {eorder}，得 {r.order_no}"
        assert ecity in r.address, f"[{i}] 地址期望含 {ecity}，得 {r.address}"
        assert "  " not in r.address, f"[{i}] 地址含连续空格: {r.address!r}"
        print(f"[{i}] {status} | {r.name} | {r.phone} | D:{r.order_no} | {r.source}")
        print(f"     地址: {r.address[:55]}...")

    if ok < 4:
        raise SystemExit("逗号正序样例解析失败")
    print("\n逗号正序样例全部通过")


if __name__ == "__main__":
    main()
