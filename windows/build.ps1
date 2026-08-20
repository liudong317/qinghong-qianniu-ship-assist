# Qinghong Qianniu Ship Assistant - single file build
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Removing old exe..."
Get-ChildItem -Path $PSScriptRoot -Filter "*.exe" -File -ErrorAction SilentlyContinue | Remove-Item -Force
if (Test-Path "dist") {
    Get-ChildItem -Path "dist" -Filter "*.exe" -File -ErrorAction SilentlyContinue | Remove-Item -Force
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -q

Copy-Item "5.15新表格.xlsx" "template.xlsx" -Force

Write-Host "Building..."
pyinstaller --noconfirm --clean --onefile --windowed `
    --name "QinghongQianniu" `
    --icon "1.ico" `
    --add-data "template.xlsx;." `
    --add-data "config.json;." `
    --add-data "1.png;." `
    --add-data "1.ico;." `
    --collect-all customtkinter `
    --collect-all tksheet `
    --hidden-import "PIL._tkinter_finder" `
    main.py

# 用 Python 复制中文文件名，避免 PowerShell 编码乱码
python -c @"
import shutil
from pathlib import Path
root = Path('.')
src = root / 'dist' / 'QinghongQianniu.exe'
if not src.exists():
    raise SystemExit('Build failed: dist/QinghongQianniu.exe not found')
name = '晴红千牛发货助手.exe'
shutil.copy2(src, root / 'dist' / name)
shutil.copy2(src, root / name)
src.unlink(missing_ok=True)
mb = (root / name).stat().st_size / 1024 / 1024
print(f'Done: {name} ({mb:.1f} MB)')
"@
