# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Read version from code_editor.py
import re
with open('code_editor.py', 'r', encoding='utf-8') as f:
    content = f.read()
    version_match = re.search(r'version\s*=\s*["\'](.+?)["\']', content)
    version = version_match.group(1) if version_match else '1.0.0'

a = Analysis(
    ['code_editor.py'],
    pathex=[],
    binaries=[],
    datas=[('icon', 'icon')],
    hiddenimports=['PIL._tkinter_finder'],
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
    name=f'CodeForge-{version}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon\\white-transparent.png'
)
