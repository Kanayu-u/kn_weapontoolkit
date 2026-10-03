"""メインウィンドウ: 左のナビと4ページ、ファイルメニュー。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from .. import APP_DISPLAY_NAME, __version__, paths
from ..i18n import tr
from ..model import PROJECT_SUFFIX, Project, ProjectError
from .components_page import ComponentsPage
from .export_page import ExportPage
from .import_dialog import ImportDialog
from .settings_dialog import SettingsDialog
from .state import AppState
from .stats_page import StatsPage
from .weapon_page import WeaponPage
from .widgets import label

REPO_URL = 'https://github.com/Kanayu-u/kn_weapontoolkit'
DISCORD_URL = 'https://discord.gg/9jXjrSp5wq'


class MainWindow(QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.resize(1120, 720)
        self.setMinimumSize(940, 600)
        self.setAcceptDrops(True)

        root = QWidget()
        root.setObjectName('root')
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # --- 左のナビ
        side = QWidget()
        side.setObjectName('sidebar')
        side.setFixedWidth(196)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(12, 18, 12, 14)
        sv.setSpacing(4)
        sv.addWidget(label('KN WTK', 'brand'))
        sv.addWidget(label(APP_DISPLAY_NAME, 'brandSub'))
        sv.addSpacing(16)

        self.stack = QStackedWidget()
        self.weapon_page = WeaponPage(state)
        self.stats_page = StatsPage(state)
        self.components_page = ComponentsPage(state)
        self.export_page = ExportPage(state)
        self.nav = QButtonGroup(self)
        pages = [(tr('1. 武器'), self.weapon_page), (tr('2. 性能'), self.stats_page),
                 (tr('3. コンポーネント'), self.components_page), (tr('4. 書き出し'), self.export_page)]
        for i, (text, page) in enumerate(pages):
            b = QPushButton(text)
            b.setObjectName('nav')
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav.addButton(b, i)
            sv.addWidget(b)
            self.stack.addWidget(page)
        self.nav.idClicked.connect(self.stack.setCurrentIndex)
        self.nav.button(0).setChecked(True)
        sv.addSpacing(10)
        # 「ファイル > 新規」と同じ。アプリを落とさずに次の武器へ移れるよう、見える所にも置く
        self.reset_btn = QPushButton('↺  ' + tr('リセット'))
        self.reset_btn.setObjectName('reset')
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setToolTip(tr('選んだテンプレート・名前・フォルダ・部品・性能の変更をすべて消して、最初から作り直します。'))
        self.reset_btn.clicked.connect(self.new_project)
        sv.addWidget(self.reset_btn)
        sv.addStretch(1)
        sv.addWidget(label(f'v{__version__}', 'faint'))
        h.addWidget(side)
        h.addWidget(self.stack, 1)

        self._build_menu()
        state.changed.connect(self._update_title)
        state.project_replaced.connect(self._update_title)
        self._update_title()

    def _build_menu(self) -> None:
        m = self.menuBar().addMenu(tr('ファイル(&F)'))
        for text, key, slot in [
            (tr('新規(&N)'), QKeySequence.StandardKey.New, self.new_project),
            (tr('開く(&O)…'), QKeySequence.StandardKey.Open, self.open_project),
            (tr('保存(&S)'), QKeySequence.StandardKey.Save, self.save_project),
            (tr('名前を付けて保存(&A)…'), QKeySequence.StandardKey.SaveAs, self.save_project_as),
        ]:
            a = QAction(text, self)
            a.setShortcut(key)
            a.triggered.connect(slot)
            m.addAction(a)
        m.addSeparator()
        a = QAction(tr('テンプレートを取り込む(&I)…'), self)
        a.triggered.connect(self.import_templates)
        m.addAction(a)
        a = QAction(tr('取り込んだテンプレートのフォルダを開く'), self)
        a.triggered.connect(self.open_user_templates)
        m.addAction(a)
        m.addSeparator()
        a = QAction(tr('設定(&P)…'), self)
        a.triggered.connect(self.open_settings)
        m.addAction(a)
        m.addSeparator()
        a = QAction(tr('終了(&X)'), self)
        a.triggered.connect(self.close)
        m.addAction(a)

        m = self.menuBar().addMenu(tr('ヘルプ(&H)'))
        a = QAction(tr('このアプリについて(&A)'), self)
        a.triggered.connect(self.about)
        m.addAction(a)

    def show_page(self, index: int) -> None:
        self.nav.button(index).setChecked(True)
        self.stack.setCurrentIndex(index)

    def _update_title(self) -> None:
        name = self.state.path.name if self.state.path else tr('無題')
        self.setWindowTitle(f'{name}{" *" if self.state.dirty else ""} — {APP_DISPLAY_NAME}')

    # --- ファイル
    def _confirm_discard(self) -> bool:
        """未保存の変更を捨ててよいか。保存を選んだら保存してから True。"""
        if not self.state.dirty:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(APP_DISPLAY_NAME)
        box.setText(tr('変更が保存されていません。保存しますか?'))
        save = box.addButton(tr('保存する'), QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton(tr('保存しない'), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(tr('キャンセル'), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is save:
            return self.save_project()
        return box.clickedButton() is discard

    def new_project(self) -> None:
        if self._confirm_discard():
            self.state.set_project(Project(), None)
            self.show_page(0)

    def open_project(self) -> None:
        if not self._confirm_discard():
            return
        path, _filter = QFileDialog.getOpenFileName(self, tr('プロジェクトを開く'), self.state.settings['last_project_dir'],
                                                    tr('武器プロジェクト (*{ext});;すべてのファイル (*)', ext=PROJECT_SUFFIX))
        if path:
            self.load_path(Path(path))

    def load_path(self, path: Path) -> bool:
        try:
            project = Project.load(path)
        except ProjectError as e:
            QMessageBox.critical(self, tr('プロジェクトを開く'), tr('開けませんでした。\n{reason}', reason=str(e)))
            return False
        self.state.settings['last_project_dir'] = str(path.parent)
        self.state.set_project(project, path)
        self.show_page(0)
        return True

    def save_project(self) -> bool:
        if self.state.path is None:
            return self.save_project_as()
        return self._save_to(self.state.path)

    def save_project_as(self) -> bool:
        start = self.state.settings['last_project_dir']
        default = str(Path(start) / (self.state.project.effective_resource_name() or 'weapon')) + PROJECT_SUFFIX
        path, _filter = QFileDialog.getSaveFileName(self, tr('プロジェクトを保存'), default,
                                                    tr('武器プロジェクト (*{ext})', ext=PROJECT_SUFFIX))
        if not path:
            return False
        if not path.lower().endswith('.json'):
            path += PROJECT_SUFFIX
        return self._save_to(Path(path))

    def _save_to(self, path: Path) -> bool:
        try:
            self.state.project.save(path)
        except ProjectError as e:
            QMessageBox.critical(self, tr('プロジェクトを保存'), tr('保存できませんでした。\n{reason}', reason=str(e)))
            return False
        self.state.path = path
        self.state.dirty = False
        self.state.settings['last_project_dir'] = str(path.parent)
        self._update_title()
        return True

    def import_templates(self) -> None:
        ImportDialog(self.state, self).exec()

    def open_user_templates(self) -> None:
        d = paths.user_templates_dir()
        d.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def open_settings(self) -> None:
        SettingsDialog(self.state.settings, self).exec()
        self.export_page.load_slot_only()

    def about(self) -> None:
        QMessageBox.about(self, tr('このアプリについて'), tr(
            '<b>{name}</b> {version}<br><br>'
            'GTA V / FiveM のアドオン武器リソースを作るツールです。<br><br>'
            'Robbster 氏の vWeaponsToolkit と、Hxrv3y 氏によるフォーク'
            '(FiveM Addon Weapon Tool Kit)を参考に、新しく書き直したものです。'
            'テンプレートは両プロジェクトとその貢献者によるものを修正して同梱しています。<br><br>'
            '<a href="{url}">{url}</a>', name=APP_DISPLAY_NAME, version=__version__, url=REPO_URL)
            + '<br><br>' + tr('質問・不具合の報告・要望: {link}', link=f'<a href="{DISCORD_URL}">Discord</a>'))

    # --- ドラッグ&ドロップ(フォルダ=モデルのフォルダ、.json=プロジェクト)
    @staticmethod
    def _dropped_path(e) -> Path | None:
        urls = e.mimeData().urls()
        if len(urls) != 1 or not urls[0].isLocalFile():
            return None
        return Path(urls[0].toLocalFile())

    def dragEnterEvent(self, e):
        p = self._dropped_path(e)
        if p is not None and (p.is_dir() or p.suffix.lower() == '.json'):
            e.acceptProposedAction()

    def dropEvent(self, e):
        p = self._dropped_path(e)
        if p is None:
            return
        if p.is_dir():
            self.show_page(0)
            self.weapon_page.set_import_dir(str(p))
        elif self._confirm_discard():
            self.load_path(p)

    def closeEvent(self, e: QCloseEvent) -> None:
        if self._confirm_discard():
            e.accept()
        else:
            e.ignore()
