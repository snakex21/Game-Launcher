# -*- mode: python ; coding: utf-8 -*-
# Build:  pyinstaller --noconfirm game_launcher.spec
# Wynik:  dist\GameLauncher\GameLauncher.exe  (tryb --onedir: szybszy start,
#         a data\ tworzy się obok exe - dobre na pendrive).
#
# Do paczki NIE trafiają dane użytkownika (data\, images\, internal_music\,
# local_settings.json) - tylko ikony, ikona aplikacji i pliki *.example.json.

import os

block_cipher = None
ROOT = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(ROOT, "icons"), "icons"),
    (os.path.join(ROOT, "icon.ico"), "."),
    (os.path.join(ROOT, "config.example.json"), "."),
    (os.path.join(ROOT, "local_settings.example.json"), "."),
    (os.path.join(ROOT, "external", "ScriptHookConfig.ini"), "external"),
]

# Moduły ładowane leniwie (importlib / _LazyModule w game_launcher.py),
# których PyInstaller nie wykryje statycznie.
hiddenimports = []
for package_dir in ("launcher", "ui", "utils", "cloud"):
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, package_dir)):
        if "__pycache__" in dirpath:
            continue
        rel = os.path.relpath(dirpath, ROOT).replace(os.sep, ".")
        for name in files:
            if name.endswith(".py") and name != "__init__.py":
                hiddenimports.append(f"{rel}.{name[:-3]}")
hiddenimports += [
    "pystray._win32",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    "engineio.async_drivers.threading",
    "tkhtmlview",
    "feedparser",
    "matplotlib.backends.backend_tkagg",
    "PIL._tkinter_finder",
]

a = Analysis(
    [os.path.join(ROOT, "game_launcher.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "tests",
        # Google Drive w aplikacji to niedzialajacy stub (importy leniwe w
        # game_launcher.py) - nie pakujemy googleapiclient (~89 MB), jesli
        # akurat jest zainstalowany w srodowisku budowania.
        "googleapiclient",
        "google",
        "google_auth_oauthlib",
        "google_auth_httplib2",
        "httplib2",
        # Narzedzia deweloperskie, ktore potrafia wpasc z globalnego Pythona.
        "IPython",
        "jedi",
        "parso",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GameLauncher",
    icon=os.path.join(ROOT, "icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GameLauncher",
)
