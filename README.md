# 晴红千牛发货助手

把京东 / 抖音 / 快手 / 千牛等平台复制的乱序收货地址，解析成千牛批量发货 Excel（A~I 列）。

支持 **Windows** 与 **macOS（Apple Silicon M1/M2/M3/M4）**，依赖打进安装包，客户无需安装 Python。

## 目录

| 路径 | 说明 |
|------|------|
| [`windows/`](windows/) | Windows 源码与 `build.ps1` |
| [`mac/`](mac/) | macOS 源码、`build.sh`、[安装说明](mac/Mac安装说明.md) |
| [`releases/`](releases/) | 可直接分发的安装包 |

## 下载安装包

- Windows：[`releases/晴红千牛发货助手.exe`](releases/晴红千牛发货助手.exe)
- macOS：[`releases/晴红千牛发货助手-macOS.app.zip`](releases/晴红千牛发货助手-macOS.app.zip)  
  解压后双击 `.app`；若提示无法验证开发者，见 [`mac/Mac安装说明.md`](mac/Mac安装说明.md)

## 版本

当前对齐 **v1.4.3**

## 自行打包

```bash
# Windows（PowerShell）
cd windows
.\build.ps1

# macOS（Apple Silicon）
cd mac
chmod +x build.sh
./build.sh
```

## 联系

开发者微信：`ziyouxiaoqi123`（备注来意）  
官网：https://www.qinghong.tech/
