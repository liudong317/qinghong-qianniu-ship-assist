"""本地解析验收脚本。"""

from src.exporter import export_to_xlsx
from src.keywords import apply_keyword_hits
from src.parser import parse_batch

SAMPLES = [
    "蔺玉泉[9196]15781066479天津市天津市河东区富民路街道月牙河南路与娄山道交叉路口往北约100米金月湾花园7号楼603[9196]",
    "四川省广安市广安区 中桥街道四川省广安市广安区金安大道三段299号华冠城1701，漆洪兰，13541869970",
]

raw = "\n\n".join(SAMPLES)
results = parse_batch(raw, ai_client=None, use_ai=False)
apply_keyword_hits(results, ["驿站", "工商局", "质检局"])

for i, r in enumerate(results, 1):
    print(f"--- 样本 {i} ---")
    print(f"  收件人: {r.name}")
    print(f"  手机:   {r.phone}")
    print(f"  地址:   {r.address}")
    print(f"  编号:   {r.order_no}")
    print(f"  来源:   {r.source}")
    print(f"  OK:     {r.ok}")

out = export_to_xlsx(results, "test_output.xlsx", extract_order_no_to_d=False)
print(f"\n已导出: {out}")
