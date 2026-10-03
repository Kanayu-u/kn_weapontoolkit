"""テンプレートの取り込み: meta の入ったフォルダを読み、選んだ武器・部品をテンプレートとして保存する。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout)

from .. import importer, paths
from ..i18n import tr
from . import theme
from .state import AppState
from .widgets import label


class ImportDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.idx: importer.MetaIndex | None = None
        self.setWindowTitle(tr('テンプレートを取り込む'))
        self.resize(980, 640)

        self.dir_edit = QLineEdit()
        self.dir_edit.setReadOnly(True)
        self.dir_edit.setPlaceholderText(tr('meta の入ったフォルダ(サブフォルダも読みます)'))
        browse = QPushButton(tr('参照…'))
        browse.clicked.connect(self.browse)
        top = QHBoxLayout()
        top.addWidget(self.dir_edit, 1)
        top.addWidget(browse)

        self.summary = label(tr('OpenIV / CodeWalker で書き出したバニラの meta や、アドオン武器のリソースのフォルダを選んでください。'),
                             'muted', wrap=True)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr('名前で絞り込み'))
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)

        self.weapons = self._tree([tr('武器'), tr('状態'), tr('動作・構え方')])
        self.components = self._tree([tr('部品'), tr('状態'), tr('取り付けボーン')])
        lists = QHBoxLayout()
        for title, tree in ((tr('武器'), self.weapons), (tr('部品'), self.components)):
            col = QVBoxLayout()
            col.addWidget(label(title, 'h2'))
            col.addWidget(tree, 1)
            lists.addLayout(col, 1)

        select_new = QPushButton(tr('新規だけ選ぶ'))
        select_new.clicked.connect(lambda: self._select(lambda it: it.data(1, Qt.ItemDataRole.UserRole) == 'new'))
        select_none = QPushButton(tr('選択を外す'))
        select_none.clicked.connect(lambda: self._select(lambda it: False))
        self.import_btn = QPushButton(tr('取り込む'))
        self.import_btn.setObjectName('primary')
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.do_import)
        close = QPushButton(tr('閉じる'))
        close.clicked.connect(self.reject)
        bottom = QHBoxLayout()
        bottom.addWidget(select_new)
        bottom.addWidget(select_none)
        bottom.addStretch(1)
        bottom.addWidget(label(tr('保存先: {path}', path=str(paths.user_templates_dir())), 'faint'))
        bottom.addWidget(self.import_btn)
        bottom.addWidget(close)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)
        root.addLayout(top)
        root.addWidget(self.summary)
        root.addWidget(self.filter)
        root.addLayout(lists, 1)
        root.addLayout(bottom)

    @staticmethod
    def _tree(headers: list[str]) -> QTreeWidget:
        t = QTreeWidget()
        t.setRootIsDecorated(False)
        t.setAlternatingRowColors(True)
        t.setHeaderLabels(headers)
        t.setColumnWidth(0, 230)
        t.setColumnWidth(1, 90)
        return t

    def browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr('meta の入ったフォルダを選ぶ'), self.dir_edit.text())
        if d:
            self.load(d)

    def load(self, folder: str) -> None:
        self.dir_edit.setText(folder)
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.idx = importer.MetaIndex.scan([folder])
        finally:
            QGuiApplication.restoreOverrideCursor()
        lib = self.state.lib
        have_w = {n: lib.weapon(n).source for n in lib.weapon_names() if self._readable(lib.weapon, n)}
        have_c = {n: lib.component(n).source for n in lib.component_names() if self._readable(lib.component, n)}
        bones = self.idx.bone_counts()
        self.weapons.clear()
        self.components.clear()
        for w in self.idx.importable_weapons():
            donor = importer.choose_donor(w, lib)
            if self.idx.own_animations(w.name):
                how = tr('この中にある')
            elif donor:
                how = tr('{name} から借用', name=donor)
            else:
                how = tr('無し(書き出し時に注意)')
            self.weapons.addTopLevelItem(self._row([w.name, '', how], w.name, have_w.get(w.name)))
        for c in self.idx.importable_components():
            counts = bones.get(c.name)
            bone = counts.most_common(1)[0][0] if counts else tr('推測')
            self.components.addTopLevelItem(self._row([c.name, '', bone], c.name, have_c.get(c.name)))
        nw, nc = self.weapons.topLevelItemCount(), self.components.topLevelItemCount()
        text = tr('{files} 個の meta を読みました。武器 {w} 種、部品 {c} 種。', files=self.idx.files, w=nw, c=nc)
        if self.idx.truncated:
            text += ' ' + tr('ファイルが多すぎるため、途中で探すのをやめました。meta の入ったフォルダだけを選んでください。')
        if self.idx.unreadable:
            text += ' ' + tr('読めなかったファイル: {n} 個(XML でない meta など)', n=len(self.idx.unreadable))
        self.summary.setText(text)
        self.import_btn.setEnabled(bool(nw or nc))
        self._apply_filter(self.filter.text())

    @staticmethod
    def _readable(getter, name: str) -> bool:
        try:
            getter(name)
            return True
        except Exception:   # 壊れたテンプレートは「無い」扱い(取り込みで直せる)
            return False

    def _row(self, cols: list[str], name: str, existing: str | None) -> QTreeWidgetItem:
        if existing is None:
            status, key, color, checked = tr('新規'), 'new', theme.T['ok'], True
        elif existing == 'user':
            status, key, color, checked = tr('取り込み済み'), 'user', theme.T['muted'], False
        else:
            status, key, color, checked = tr('同梱にある'), 'bundled', theme.T['muted'], False
        cols[1] = status
        it = QTreeWidgetItem(cols)
        it.setData(0, Qt.ItemDataRole.UserRole, name)
        it.setData(1, Qt.ItemDataRole.UserRole, key)
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        it.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        it.setForeground(1, QColor(color))
        if existing:
            it.setToolTip(1, tr('取り込むと、こちらが優先して使われます。'))
        return it

    def _items(self, tree: QTreeWidget) -> list[QTreeWidgetItem]:
        return [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().upper()
        for tree in (self.weapons, self.components):
            for it in self._items(tree):
                it.setHidden(bool(needle) and needle not in it.text(0).upper())

    def _select(self, pred) -> None:
        for tree in (self.weapons, self.components):
            for it in self._items(tree):
                if not it.isHidden():
                    it.setCheckState(0, Qt.CheckState.Checked if pred(it) else Qt.CheckState.Unchecked)

    def checked(self, tree: QTreeWidget) -> list[str]:
        return [it.data(0, Qt.ItemDataRole.UserRole) for it in self._items(tree)
                if it.checkState(0) == Qt.CheckState.Checked]

    def do_import(self) -> None:
        if self.idx is None:
            return
        weapons, components = self.checked(self.weapons), self.checked(self.components)
        if not weapons and not components:
            QMessageBox.information(self, self.windowTitle(), tr('取り込むものが選ばれていません。'))
            return
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            failed = importer.import_into(self.idx, Path(paths.user_templates_dir()), self.state.lib, weapons,
                                          components)
        finally:
            QGuiApplication.restoreOverrideCursor()
        self.state.templates_changed.emit()
        done = len(weapons) + len(components) - len(failed)
        text = tr('{n} 個のテンプレートを取り込みました。', n=done)
        if failed:
            text += '\n' + tr('取り込めなかったもの:') + '\n' + '\n'.join(f'{n}: {r}' for n, r in failed[:20])
        QMessageBox.information(self, self.windowTitle(), text)
        if not failed:
            self.accept()
