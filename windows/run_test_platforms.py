"""三平台客户粘贴样例：京东(姓名空行手机)、抖音(逗号正序)、京东(多行带编号)。"""

from pathlib import Path

from src.parser import parse_batch, split_records
from src.validators import apply_phone_validation

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "测试样例-三平台.txt"

EXPECTED = [
    ("陈禄寿", "13594567686", "", "涪陵"),
    ("刘忠妹", "15781254018", "4449", "信丰"),
    ("许闪闪[6797]", "18825717091", "6797", "东莞"),
]


def main():
    raw = SAMPLES.read_text(encoding="utf-8").strip()
    records = split_records(raw)
    print(f"分隔得到 {len(records)} 条\n")
    for i, rec in enumerate(records, 1):
        print(f"--- record {i} ---\n{rec!r}\n")
    assert len(records) == 3, f"期望3条，实际{len(records)}"

    results = parse_batch(raw, use_ai=False)
    apply_phone_validation(results)

    ok = 0
    for i, (r, (ename, ephone, eorder, ecity)) in enumerate(zip(results, EXPECTED), 1):
        status = "OK" if r.ok else "FAIL"
        if r.ok:
            ok += 1
        assert r.name == ename, f"[{i}] 姓名期望 {ename}，得 {r.name}"
        assert r.phone == ephone, f"[{i}] 手机期望 {ephone}，得 {r.phone}"
        if eorder:
            assert r.order_no == eorder, f"[{i}] 后缀期望 {eorder}，得 {r.order_no}"
        assert ecity in r.address, f"[{i}] 地址期望含 {ecity}，得 {r.address}"
        print(f"[{i}] {status} | {r.name} | {r.phone} | D:{r.order_no} | {r.source}")
        print(f"     地址: {r.address[:60]}...")

    if ok < 3:
        raise SystemExit("三平台样例解析失败")
    print("\n三平台样例全部通过")


if __name__ == "__main__":
    main()
