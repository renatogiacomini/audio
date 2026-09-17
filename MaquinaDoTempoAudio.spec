# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

project = Path(SPEC).resolve().parent

datas = [(str(project / "assets"), "assets")]
datas += collect_data_files("imageio_ffmpeg")

binaries = []
binaries += collect_dynamic_libs("soundfile")
binaries += collect_dynamic_libs("imageio_ffmpeg")

hiddenimports = [
    "pydub",
    "imageio_ffmpeg",
    "soundfile",
    "sounddevice",
    "scipy.signal",
    "PIL.Image",
    "PIL.ImageTk",
    "matplotlib.backends.backend_tkagg",
]

a = Analysis(
    [str(project / "maquina_tempo_audio_v2_3_portable.py")],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MaquinaDoTempoAudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
