"""多行地址样例测试。"""

from pathlib import Path

from src.parser import parse_batch, split_records
from src.validators import apply_phone_validation

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "测试样例-多行.txt"

EXPECTED = [
    ("尤长军", "06636209024", "台州"),
    ("赖瑞洪", "18400849612", "厦门"),
    ("覃文举", "18400815834", "嘉兴"),
    ("曾丽英", "17896086034", "成都"),
    ("张琴", "18825706409", "靖江"),
]


def main():
    raw = SAMPLES.read_text(encoding="utf-8").strip()
    records = split_records(raw)
    print(f"分隔得到 {len(records)} 条\n")
    assert len(records) == 5, f"期望5条，实际{len(records)}"

    results = parse_batch(raw, use_ai=False)
    apply_phone_validation(results)

    ok = 0
    for i, (r, (ename, ephone, ecity)) in enumerate(zip(results, EXPECTED), 1):
        status = "OK" if r.ok else "FAIL"
        if r.ok:
            ok += 1
        assert ename in r.name, f"[{i}] 姓名期望含 {ename}，得 {r.name}"
        assert r.phone == ephone, f"[{i}] 手机期望 {ephone}，得 {r.phone}"
        assert ecity in r.address, f"[{i}] 地址期望含 {ecity}，得 {r.address}"
        print(f"[{i}] {status} | {r.name} | {r.phone} | {r.source}")
        print(f"     地址: {r.address[:60]}...")

    if ok < 5:
        raise SystemExit("多行样例解析失败")
    print("\n多行样例全部通过")


if __name__ == "__main__":
    main()
