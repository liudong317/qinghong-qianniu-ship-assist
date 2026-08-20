# -*- mode: python ; coding: utf-8 -*-
# macOS PyInstaller spec — 晴红千牛发货助手 v1.4.3
from PyInstaller.utils.hooks import collect_all

datas = [
    ('template.xlsx', '.'),
    ('config.json', '.'),
    ('1.png', '.'),
    ('1.ico', '.'),
    ('app_icon.png', '.'),
    ('1.icns', '.'),
]
binaries = []
hiddenimports = ['PIL._tkinter_finder']

tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('tksheet')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='QinghongQianniu',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    icon=['1.icns'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='QinghongQianniu',
)

app = BUNDLE(
    coll,
    name='QinghongQianniu.app',
    icon='1.icns',
    bundle_identifier='tech.qinghong.qianniu.shipassist',
    info_plist={
        'CFBundleDisplayName': '晴红千牛发货助手',
        'CFBundleName': '晴红千牛发货助手',
        'CFBundleShortVersionString': '1.4.3',
        'CFBundleVersion': '1.4.3',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
