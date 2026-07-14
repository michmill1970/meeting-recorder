# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Meeting Recorder.

Build command:
    pyinstaller meeting-recorder.spec

Output:
    dist/Meeting Recorder.app  — macOS application bundle
    dist/meeting-recorder      — Linux/Windows executable
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all hidden imports that PyInstaller can't detect automatically
hidden_imports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "pyaudio",
    "openai",
    "anthropic",
    "requests",
    "numpy",
    "mlx_whisper",
    "pyannote.audio",
    "torch",
    "torchaudio",
    "omegaconf",
]

a = Analysis(
    ["src/main.py"],
    pathex=[],
    binaries=[],
    datas=[
        # Include the vendored whisper-diarization directory
        ("whisper-diarization", "whisper-diarization"),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "email",
        "http",
        "xml",
        "jinja2",
        "setuptools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# macOS app bundle
app = App(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Meeting Recorder",
    icon="icons/meeting-recorder-icon.png",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="x86_64",  # Will be overridden by --arch flag
    codesign_identity=None,
    entitlements_file=None,
)
