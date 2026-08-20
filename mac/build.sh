#!/usr/bin/env bash
# 晴红千牛发货助手 — macOS (Apple Silicon) 打包
# 产出：dist/晴红千牛发货助手.app（依赖全部打入，双击即可用）
set -euo pipefail
cd "$(dirname "$0")"

APP_DISPLAY_NAME="晴红千牛发货助手"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

echo "==> Python: $($PYTHON_BIN --version)"
echo "==> Arch: $(uname -m)"

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -U pip -q
pip install -r requirements.txt -q

cp -f "5.15新表格.xlsx" "template.xlsx"

if [[ ! -f 1.icns ]]; then
  echo "缺少 1.icns，请先生成图标（assets/AppIcon.iconset → iconutil）"
  exit 1
fi

echo "==> PyInstaller 打包 .app（QinghongQianniu.spec）..."
arch -arm64 pyinstaller --noconfirm --clean QinghongQianniu.spec

SRC_APP="dist/QinghongQianniu.app"
DST_APP="dist/${APP_DISPLAY_NAME}.app"
if [[ ! -d "$SRC_APP" ]]; then
  echo "打包失败：未找到 $SRC_APP"
  exit 1
fi
rm -rf "$DST_APP"
mv "$SRC_APP" "$DST_APP"

# 工程根目录也放一份方便分发
rm -rf "./${APP_DISPLAY_NAME}.app"
cp -R "$DST_APP" "./${APP_DISPLAY_NAME}.app"

SIZE=$(du -sh "./${APP_DISPLAY_NAME}.app" | awk '{print $1}')
echo "==> 完成: ${APP_DISPLAY_NAME}.app (${SIZE})"
echo "    路径: $(pwd)/${APP_DISPLAY_NAME}.app"
echo "    以及: $(pwd)/dist/${APP_DISPLAY_NAME}.app"
echo ""
echo "提示：首次打开若被 Gatekeeper 拦截，可右键 → 打开。"
echo "配置与历史：~/Library/Application Support/${APP_DISPLAY_NAME}/"
