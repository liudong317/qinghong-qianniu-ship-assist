# 晴红千牛发货助手 — macOS 版

对齐 Windows **v1.4.3**，业务逻辑一致；依赖全部打进 `.app`，客户无需安装 Python。

## 目录说明

```
晴红表格梳理-Mac/
├── main.py                 # 入口
├── build.sh                # Mac 一键打包（arm64 .app）
├── QinghongQianniu.spec    # PyInstaller spec（备选）
├── requirements.txt
├── config.json
├── template.xlsx / 5.15新表格.xlsx
├── 1.png / 1.ico / 1.icns / app_icon.png   # Logo 与图标
├── assets/                 # 图标源与 iconset
├── src/                    # 业务与 GUI（与 Win 同逻辑，含 Mac 适配）
├── docs/                   # 需求 / 设计 / 移植说明
├── 测试样例-*.txt
├── run_test*.py
└── README-Mac.md           # 本文档
```

## Mac 相对 Win 的适配

| 项 | 说明 |
|----|------|
| 配置/历史 | 写入 `~/Library/Application Support/晴红千牛发货助手/`（.app 内只读） |
| 字体 | `PingFang SC` 等，避免雅黑缺失 |
| 图标 | `.icns` 作 Dock；窗口用 PNG |
| 右键菜单 | 支持 Button-2 / Control-Click |

## 开发运行

```bash
cd 晴红表格梳理-Mac
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 跑测试

```bash
source .venv/bin/activate
python run_test_platforms.py
python run_test.py
python run_test_multiline.py
python run_test_comma_fwd.py
```

## 打包

```bash
chmod +x build.sh
./build.sh
```

产物：

- `晴红千牛发货助手.app`
- `dist/晴红千牛发货助手.app`

也可：`pyinstaller QinghongQianniu.spec`

## 分发注意

未签名时，用户可能需：**右键 → 打开**，或在「隐私与安全性」里允许。
若需正式分发，请用 Apple Developer 证书 codesign + notarize。
