# PyInstaller spec — `pyinstaller kn_weapontoolkit.spec` (scripts/build.ps1 経由で実行)
# 構成: onedir。templates/ は build.ps1 が exe の隣へコピーする(利用者がテンプレートを足せる場所にするため)。
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # 標準ライブラリを名前だけ指定するとパッケージの __init__ しか入らないので、サブモジュールごと集める
    hiddenimports=collect_submodules('xml') + collect_submodules('kn_weapontoolkit'),
    excludes=['tkinter', 'unittest', 'PySide6.QtWebEngineCore', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.Qt3DCore',
              'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PySide6.QtCharts', 'PySide6.QtDataVisualization',
              'PySide6.QtBluetooth', 'PySide6.QtPositioning', 'PySide6.QtSql', 'PySide6.QtNetwork'],
    noarchive=False,
)
pyz = PYZ(a.pure)
# 開発時と同じく UTF-8 モードで動かす
utf8 = [('X utf8', None, 'OPTION')]
exe = EXE(pyz, a.scripts, utf8, exclude_binaries=True, name='kn_weapontoolkit', console=False, debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, icon='assets/kn_weapontoolkit.ico', version=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='kn_weapontoolkit')
