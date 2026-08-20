"""路径与配置工具。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

APP_SUPPORT_NAME = "晴红千牛发货助手"

DEFAULT_CONFIG = {
    "keywords": ["驿站", "工商局", "质检局"],
    "keyword_mode": "contains",
    "extract_order_no_to_d": False,
    "record_separator": "auto",
    "custom_separator": "",
    "keyword_scan": {
        "name": True,
        "address": True,
        "phone": False,
        "remark": False,
    },
    "highlight_colors": {
        "keyword_hit": "#FF4444",
        "parse_warn": "#FFFF99",
    },
    "font_sizes": {
        "input_left": 14,
        "table_right": 13,
    },
    "ai": {
        "enabled": True,
        "base_url": "https://www.qinghong.tech/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "system_prompt": "",
        "register_url": "https://www.qinghong.tech/",
        "docs_url": "https://qinghongkeji.apifox.cn/",
    },
}


def _is_macos_app_bundle(exe: Path) -> bool:
    """判断是否运行在 .app/Contents/MacOS 内。"""
    parts = exe.parts
    try:
        idx = parts.index("Contents")
        return idx > 0 and parts[idx - 1].endswith(".app") and exe.parent.name == "MacOS"
    except ValueError:
        return False


def app_dir() -> Path:
    """可写目录：开发态为工程根；Mac .app 用 Application Support；其余为可执行文件旁。"""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        if sys.platform == "darwin" and _is_macos_app_bundle(exe):
            support = Path.home() / "Library" / "Application Support" / APP_SUPPORT_NAME
            support.mkdir(parents=True, exist_ok=True)
            return support
        return exe.parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """只读资源目录（PyInstaller _MEIPASS 或工程根）。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def resource_path(name: str) -> Path:
    bundled = bundle_dir() / name
    if bundled.exists():
        return bundled
    # 开发态兼容 assets/ 下的图标
    assets = bundle_dir() / "assets" / name
    if assets.exists():
        return assets
    return app_dir() / name


def config_path() -> Path:
    user_cfg = app_dir() / "config.json"
    if user_cfg.exists():
        return user_cfg
    return resource_path("config.json")


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    merged = DEFAULT_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if k not in ("ai", "keyword_scan", "highlight_colors", "font_sizes")})
    merged["keyword_scan"] = {**DEFAULT_CONFIG["keyword_scan"], **data.get("keyword_scan", {})}
    merged["highlight_colors"] = {**DEFAULT_CONFIG["highlight_colors"], **data.get("highlight_colors", {})}
    merged["font_sizes"] = {**DEFAULT_CONFIG["font_sizes"], **data.get("font_sizes", {})}
    merged["ai"] = {**DEFAULT_CONFIG["ai"], **data.get("ai", {})}
    return merged


def save_config(data: dict) -> None:
    path = app_dir() / "config.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
