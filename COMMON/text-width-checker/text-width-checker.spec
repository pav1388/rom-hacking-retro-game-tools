# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['text-width-checker.pyw'],
    pathex=[],
    binaries=[],
    datas=[],  # Добавляем файлы
    hiddenimports=['tkinter', 'json', 'os'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='text-width-checker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False для GUI приложения (без консоли)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='32bit',  # Для 32-битной версии
    codesign_identity=None,
    entitlements_file=None,
    icon=None  # указать путь к иконке: 'icon.ico'
)