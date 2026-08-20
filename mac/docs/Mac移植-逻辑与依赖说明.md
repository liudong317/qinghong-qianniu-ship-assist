# 晴红千牛发货助手 — Mac（Apple Silicon / M 芯片）移植说明

> 版本对齐：Windows **v1.4.3**  
> 用途：把 Win 版全部业务逻辑、依赖、打包方式完整交给 Mac 侧 AI 复刻一版（功能等价）  
> 源工程：`晴红表格梳理`（Python + CustomTkinter + tksheet）

---

## 1. 产品目标（不变）

把客户从 **京东 / 抖音 / 快手 / 千牛聊天** 等处**手动复制**的乱序收货文字，解析成千牛批量发货 Excel（A~I 列），并支持关键词整行标红、可选晴红 AI 兜底。

**交付形态：**

| 平台 | 交付物 | 要求 |
|------|--------|------|
| Windows | `晴红千牛发货助手.exe` | **单文件**，依赖全部打进 exe |
| macOS (M1/M2/M3/M4) | `.app`（建议 arm64 原生） | **同等功能**；依赖打进 app，客户双击即可用 |

---

## 2. 仓库结构（Win 现状）

```
晴红表格梳理/
├── main.py                 # 入口
├── build.ps1               # Win PyInstaller 打包
├── requirements.txt
├── config.json             # 默认配置（Key 不写死）
├── template.xlsx / 5.15新表格.xlsx
├── 1.png / 1.ico           # Logo / 图标
├── src/
│   ├── gui.py              # GUI 主界面 v1.4.3
│   ├── parser.py           # 核心解析（规则 + 分隔）
│   ├── ai_client.py        # OpenAI 兼容 API 客户端
│   ├── ai_prompts.py       # AI 提示词
│   ├── exporter.py         # 导出 xlsx + 整行标红
│   ├── template_columns.py # A~I 表头对齐
│   ├── validators.py       # 手机号校验提示
│   ├── keywords.py         # 关键词命中
│   ├── batch_io.py         # txt/xlsx 导入、TSV、批量替换
│   ├── history.py          # 历史批次
│   ├── config.py           # 路径/配置（frozen 资源）
│   ├── colors.py           # 颜色工具
│   ├── ui_utils.py         # 对话框置顶、文件选择、导出文件名
│   └── usage_guide.py      # 使用说明文案
├── 测试样例-*.txt
├── run_test*.py
└── Mac移植-逻辑与依赖说明.md   # 本文档
```

---

## 3. 千牛输出列（A~I）

与模板 `5.15新表格.xlsx` 第一行一致：

| 列 | 字段 | 必填 | 来源 |
|----|------|------|------|
| A | 收件人 | 是 | `name`（保留 `[四位]`） |
| B | 手机号 | 是 | 11 位（`1` 实号或 `0` 虚拟号） |
| C | 收货地址 | 是 | `address`（保留 `[四位]`；连续空格合并） |
| D | 平台订单号 | 否 | 勾选「D列订单号」时写入：`[9196]` 或 `手机-0319` 的后缀 |
| E~H | 商品/规格/数量/重量 | 否 | 预览可手改 |
| I | 备注 | 否 | 用户备注或解析错误提示 |

---

## 4. 解析逻辑（必须 1:1 复刻）

实现文件：`src/parser.py`

### 4.1 手机号

- 实号：`1[3-9]\d{9}`
- 虚拟号（快手等）：`0\d{10}`（如 `06636209024`）
- `15782115734-0319` → B 列取前 11 位；D 列可取后缀 `0319`
- 行尾 `(虚拟号)` / `（虚拟号）` 忽略

### 4.2 订单号 `pick_order_no`

优先级：

1. 文本中 `[四位数字]`（如 `[6797]`）取第一个  
2. 否则匹配 `1xxxxxxxxxx-四位` / 全角横杠，取后缀

### 4.3 地址清洗 `_normalize_address`

- 全角空格 → 半角  
- **连续多个空格 → 单个空格**  
- **不要**去重「市市」「镇镇」、不要改驿站/大门口等原文

### 4.4 多条分隔 `split_records(separator)`

| 模式 | 行为 |
|------|------|
| `auto`（默认） | 先按空行切块；**合并**「仅姓名块 + 下一块以手机开头」的碎片（京东粘贴坑）；若无空行且存在「纯手机行」则按手机分组 |
| `blank_line` | 空行切块 + 同上碎片合并 |
| `newline` | 每非空行一条 |
| `semicolon` | `;` / `；` |
| `custom` | 自定义分隔符 |

**京东空行修复（v1.4.3 关键）：**

```
陈禄寿
<空行>          ← 不是记录分隔，必须合并
13594567686
重庆市...
```

合并后按多行规则解析。完整记录之间的空行仍作分隔。

### 4.5 单条规则优先级 `parse_with_rules`

按顺序命中即返回（成功后再 `_finalize` 洗地址）：

1. **`rule-multiline`** — 多行：姓名 / 手机 / 地址（可含 `[编号]`、虚拟号）  
2. **`rule-comma-fwd`** — 正序：`姓名，手机-后缀，地址`（中/英逗号均可）  
3. **`rule-comma`** — 倒序：`地址，姓名，手机`  
4. **`rule-compact`** — 紧凑：`姓名[编号]+手机+地址[编号]` 同行  
5. **`rule-anchor`** — 手机锚点兜底  

失败且开启 AI → `parse_with_ai`（`source=ai`）。

### 4.6 三平台客户样例（测试基准）

文件：`测试样例-三平台.txt`，测试：`run_test_platforms.py`

| 平台 | 原样特征 | 期望 |
|------|----------|------|
| 京东① | 姓名与手机之间有空行 | 陈禄寿 / 13594567686 / 重庆… |
| 抖音 | `姓名, 手机-四位, 省 市 县 …` | 刘忠妹 / 15781254018 / D=4449 |
| 京东② | `姓名[6797]` 分行 + 地址尾 `[6797]` | 许闪闪[6797] / 18825717091 / D=6797 |

其他回归：

- `run_test.py`（紧凑+倒序）  
- `run_test_multiline.py`（快手虚拟号+多行）  
- `run_test_comma_fwd.py`（逗号正序含单字姓）

---

## 5. GUI 功能清单（`src/gui.py`）

### 5.1 页头

- Logo + 标题 `晴红千牛发货助手 vX.Y.Z`  
- 副文案：Powered by 晴红AI · www.qinghong.tech  
- 按钮：使用说明 / AI配置 / 注册晴红AI / API文档 / 联系开发者（微信 `ziyouxiaoqi123`）

### 5.2 工具栏

| 按钮 | 行为 |
|------|------|
| 开始解析 | `parse_batch` → 预览表 |
| 导出Excel | 对齐模板，默认文件名中国时区 `YYYY.M.D-H.MM.xlsx` |
| 导入txt / 导入xlsx | 加载后进预览 |
| 复制TSV | 剪贴板 |
| 批量替换 | 姓名/地址/手机/备注字段 |
| 历史记录 | 恢复批次 |
| 字体大小 | 左输入 / 右表格 10~24，写入 config |
| 选项开关 | 关键词扫描列、标色、分隔方式等 |
| **重新开始** | 清空左侧文字 + 右侧表（有内容时确认）；**不**清关键词/AI 配置 |

勾选：

- **D列订单号**：导出/预览是否写 D  
- **晴红AI兜底**：规则失败是否调 AI  

状态栏：`共N条 | 成功 | 标红 | 待处理 | AI条数`

### 5.3 主区

- 左：粘贴框 + 右键复制粘贴 + 关键词标签（命中整行红）  
- 右：tksheet 九列，双击可编辑，回写 `ParseResult`

### 5.4 交互细节

- 对话框需置顶（Win 曾被主窗遮挡；Mac 也要注意模态）  
- 配置写在 **可执行文件同目录** `config.json`（不要只写只读 bundle）  
- API Key **不写死**，用户在 AI 配置里填

---

## 6. 其他模块要点

| 模块 | 职责 |
|------|------|
| `exporter.py` | openpyxl 写 xlsx；关键词命中整行填充红色 |
| `validators.py` | 非 11 位或格式异常时标记待处理/警告色 |
| `keywords.py` | contains 模式；可扫 name/address/phone/remark |
| `ai_client.py` | `POST {base_url}/chat/completions`，OpenAI 兼容；超时与错误中文提示 |
| `ai_prompts.py` | 强制 JSON：`name/phone/address`，保留 `[四位]` |
| `history.py` | 本地 JSON 历史 |
| `config.py` | `frozen` 时：资源在 `_MEIPASS`（Win）/ app Resources（Mac）；可写配置在 exe/app 旁 |

---

## 7. 依赖（`requirements.txt`）

```
openpyxl>=3.1.0
customtkinter>=5.2.0
Pillow>=10.0.0
requests>=2.31.0
tksheet>=7.6.0
pyinstaller>=6.0.0   # Win；Mac 可用 pyinstaller 或 py2app
```

系统依赖：Tk（macOS 需确保 Tcl/Tk 与 Python 匹配；可用官方 python.org 安装包或 conda）。

---

## 8. Win 打包逻辑（对照）

`build.ps1` 要点：

- `--onefile --windowed`  
- `--add-data`：`template.xlsx`、`config.json`、`1.png`、`1.ico`  
- `--collect-all customtkinter`、`--collect-all tksheet`  
- `--hidden-import PIL._tkinter_finder`  
- 输出中文名：`晴红千牛发货助手.exe`

**Mac 建议等价：**

```bash
# Apple Silicon 原生
arch -arm64 pyinstaller --noconfirm --clean --windowed --onefile \
  --name "QinghongQianniu" \
  --icon "1.icns" \
  --add-data "template.xlsx:." \
  --add-data "config.json:." \
  --add-data "1.png:." \
  --collect-all customtkinter \
  --collect-all tksheet \
  --hidden-import "PIL._tkinter_finder" \
  main.py
```

或做成 `.app`（`--windowed` 不 onefile），把资源放进 `Contents/Resources`，`config.json` 写到 `~/Library/Application Support/晴红千牛发货助手/` 或 app 同级（与 Win「旁路可写」策略一致即可）。

**必须：** 用户机器无需再装 Python / pip；所有依赖打进包。

---

## 9. Mac 侧验收清单

- [ ] 三平台样例 `测试样例-三平台.txt` 全过  
- [ ] `run_test.py` / `run_test_multiline.py` / `run_test_comma_fwd.py` 全过  
- [ ] 京东姓名与手机之间空行可解析  
- [ ] 抖音英文逗号 + `手机-四位` → D 列后缀  
- [ ] 京东 `[6797]` 保留在姓名与地址  
- [ ] 「重新开始」清空输入与预览  
- [ ] 导出 xlsx 可被千牛导入  
- [ ] 关键词整行标红  
- [ ] AI 配置可保存；无 Key 时仅规则可用  
- [ ] arm64 双击运行，无额外依赖提示  

---

## 10. 明确不要改的业务决策

1. 不自动删除地址里重复的「市」「镇」原文  
2. 不删除姓名/地址里的 `[四位]`  
3. API Key 不内置  
4. 默认分隔：`auto`（空行优先 + 碎片合并）  
5. UI 文案可微调，**解析规则与列语义必须一致**

---

## 11. 给 Mac AI 的最短开工指令

1. 复制本仓库 `src/`、`main.py`、`requirements.txt`、测试样例与 `run_test*.py`  
2. 在 Apple Silicon 上建 venv，安装依赖，跑通全部 `run_test*.py`  
3. GUI 用同一套 CustomTkinter；注意 macOS 菜单/置顶/路径  
4. 按第 8 节打 arm64 `.app` 或 onefile  
5. 用 `测试样例-三平台.txt` 做手工验收  

**逻辑源码真相以 `src/parser.py` + `src/gui.py` 为准；本文为规格摘要。**
