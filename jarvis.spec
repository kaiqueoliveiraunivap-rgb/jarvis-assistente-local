# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules


datas = [
    ("data/custom_commands.json", "data"),
    ("README.md", "."),
    ("version.json", "."),
    ("assets", "assets"),
]
binaries = []
hiddenimports = collect_submodules("jarvis")

for package in ("openwakeword", "faster_whisper"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += [
    "pythoncom",
    "pywintypes",
    "win32com.client",
    "win32com.server.util",
    "sounddevice",
    "onnxruntime",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "pycaw.pycaw",
    "comtypes",
    "screen_brightness_control",
    "PIL.ImageGrab",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tensorflow", "torch", "torchvision", "matplotlib", "pandas", "cv2", "playwright"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

jarvis = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JARVIS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/jarvis.ico",
)

jarvis_debug = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JARVIS-Debug",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon="assets/jarvis.ico",
)

coll = COLLECT(
    jarvis,
    jarvis_debug,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="JARVIS",
)
