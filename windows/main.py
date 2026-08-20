"""晴红千牛发货助手 — 程序入口。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.gui import run_app


if __name__ == "__main__":
    run_app()
