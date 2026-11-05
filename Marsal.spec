# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/projects/marsal/desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[('D:/projects/marsal/.env', '.'), ('D:/projects/marsal/src/templates', 'src/templates'), ('D:/projects/marsal/data/students_sample.csv', 'data'), ('D:/projects/marsal/data/students_sample.xlsx', 'data'), ('D:/projects/marsal/Marsal Visual Identity/logo/marsal.ico', 'Marsal Visual Identity/logo')],
    hiddenimports=['pyautogui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'scipy', 'numpy', 'pandas', 'matplotlib', 'cv2', 'sklearn', 'IPython', 'notebook', 'jupyter', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Marsal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir='.',
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/projects/marsal/Marsal Visual Identity/logo/marsal.ico'],
)
