"""GUI の起動。"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, Qt, QTranslator
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from .. import APP_DISPLAY_NAME, APP_NAME, i18n, paths
from ..i18n import tr


def _install_qt_translator(app: QApplication, lang: str) -> None:
    """QMessageBox の「はい/いいえ」など Qt 標準の文言を翻訳する。見つからなければ英語のまま。"""
    if lang == 'en':
        return
    t = QTranslator(app)
    if t.load(f'qtbase_{lang}', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(t)


def _excepthook(kind, value, tb) -> None:
    """想定外の例外で黙って落ちない。内容を見せて作業は続けられるようにする。"""
    text = ''.join(traceback.format_exception(kind, value, tb))
    sys.stderr.write(text)
    if QApplication.instance() is not None:
        box = QMessageBox(QMessageBox.Icon.Critical, APP_DISPLAY_NAME,
                          tr('予期しないエラーが起きました。作業内容は保存してから続けてください。'))
        box.setDetailedText(text)
        box.exec()


def create(argv: list[str]):
    """アプリとメインウィンドウを作って返す(スクリーンショット用のスクリプトからも使う)。"""
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setStyle('Fusion')

    from ..settings import Settings
    settings = Settings()
    lang = i18n.set_language(settings['language'])   # 画面を作る前に決める(切り替えは再起動で反映)
    _install_qt_translator(app, lang)
    from . import theme
    app.setFont(QFont(theme.font_families(lang).split(',')[0].strip('" '), 10))
    theme.apply(settings['theme'], lang)
    # 「システムに合わせる」のときは OS 側の切り替えに追従する
    app.styleHints().colorSchemeChanged.connect(lambda _scheme: theme.follow_system(settings['theme'], lang))
    app.setWindowIcon(theme.app_icon())
    if getattr(app, '_kn_autoscroll', None) is None:  # ホイールを押したまま動かして一覧を送る
        from . import autoscroll
        app._kn_autoscroll = autoscroll.install(app)

    from ..templates import TemplateLibrary
    from .main_window import MainWindow
    from .state import AppState
    lib = TemplateLibrary(paths.template_roots())
    state = AppState(settings, lib)
    win = MainWindow(state)
    return app, win


def main() -> int:
    if sys.platform.startswith('win'):
        try:  # タスクバーで python.exe ではなく本アプリのアイコンを出す
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f'kn.{APP_NAME}')
        except Exception:
            pass
    sys.excepthook = _excepthook
    app, win = create(sys.argv)
    win.show()
    if not win.state.lib.weapon_names():
        QMessageBox.critical(win, APP_DISPLAY_NAME,
                             tr('テンプレートが見つかりません。\n{path}\nアプリのフォルダに templates フォルダがあるか確認してください。',
                                path=str(paths.templates_dir())))
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args:
        p = Path(args[0])
        if p.is_dir():
            win.weapon_page.set_import_dir(str(p))
        else:
            win.load_path(p)
    return app.exec()
