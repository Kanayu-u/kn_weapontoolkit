"""4. 書き出し: 点検結果を見て、FiveM リソースとして保存する。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from .. import checks, exporter
from ..i18n import N_, tr
from ..xmlio import MetaError
from . import theme
from .state import AppState
from .widgets import card, label, page_header, repolish

_LEVEL_TEXT = {checks.ERROR: N_('エラー'), checks.WARNING: N_('注意'), checks.INFO: N_('情報')}
_LEVEL_COLOR = {checks.ERROR: 'danger', checks.WARNING: 'warn', checks.INFO: 'info'}


class ExportPage(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.setObjectName('page')
        self.state = state
        self._loading = False
        self._issues: list[checks.Issue] = []
        self._last_target: Path | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(page_header(tr('書き出し'), tr('問題が無いか点検してから、サーバーの resources に置けるフォルダとして保存します。')))

        # --- 点検
        self.pill = QLabel()
        self.pill.setObjectName('pill')
        top = QHBoxLayout()
        top.addWidget(label(tr('点検'), 'h2'))
        top.addWidget(self.pill)
        top.addStretch(1)
        root.addLayout(top)
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.setWordWrap(True)
        self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        root.addWidget(self.list, 1)

        # --- 並び順
        self.slot_auto = QCheckBox(tr('武器ホイールの並び順を自動で決める'))
        self.slot_auto.setToolTip(tr('武器ごとに重ならない番号を、書き出すときに割り当てます(次の番号は設定で変えられます)。'))
        self.slot_auto.toggled.connect(self._on_slot)
        self.slot = QSpinBox()
        self.slot.setRange(1, 99999)
        self.slot.valueChanged.connect(self._on_slot)
        srow = QHBoxLayout()
        srow.addWidget(self.slot_auto)
        srow.addSpacing(12)
        srow.addWidget(label(tr('並び順')))
        srow.addWidget(self.slot)
        srow.addStretch(1)

        # --- 出力先
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText(tr('書き出し先のフォルダ(この中にリソース名のフォルダを作ります)'))
        self.out_edit.setText(state.settings['last_export_dir'])
        self.out_edit.textChanged.connect(self._update_target)
        browse = QPushButton(tr('参照…'))
        browse.clicked.connect(self.browse)
        self.export_btn = QPushButton(tr('書き出す'))
        self.export_btn.setObjectName('primary')
        self.export_btn.clicked.connect(self.export)
        orow = QHBoxLayout()
        orow.addWidget(label(tr('書き出し先')))
        orow.addWidget(self.out_edit, 1)
        orow.addWidget(browse)
        orow.addWidget(self.export_btn)

        self.target_label = label('', 'faint')
        self.result = label('', 'okText', wrap=True)
        self.open_btn = QPushButton(tr('フォルダを開く'))
        self.open_btn.setObjectName('ghost')
        self.open_btn.clicked.connect(self._open_target)
        self.open_btn.hide()
        rrow = QHBoxLayout()
        rrow.addWidget(self.result, 1)
        rrow.addWidget(self.open_btn)

        box = QVBoxLayout()
        box.setSpacing(10)
        box.addLayout(srow)
        box.addLayout(orow)
        box.addWidget(self.target_label)
        box.addLayout(rrow)
        root.addWidget(card(box))

        # 入力のたびに点検し直すと重いので、少し待ってからまとめて実行する
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self.refresh)
        state.changed.connect(self._schedule)
        state.assets_changed.connect(self._schedule)
        state.project_replaced.connect(self.load)
        theme.notifier().changed.connect(lambda _m: self.refresh())
        self.load()

    def load(self) -> None:
        p = self.state.project
        self._loading = True
        try:
            self.slot_auto.setChecked(p.slot_order is None)
            self.slot.setEnabled(p.slot_order is not None)
            self.slot.setValue(p.slot_order if p.slot_order is not None else int(self.state.settings['next_slot']))
        finally:
            self._loading = False
        self.result.setText('')
        self.open_btn.hide()
        self.refresh()

    def _schedule(self) -> None:
        if self.isVisible():        # 見えていない間は点検しない(表示するときに showEvent で行う)
            self._timer.start()

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()

    def issues(self) -> list[checks.Issue]:
        return self._issues

    def refresh(self) -> None:
        p = self.state.project
        self._issues = checks.run(p, self.state.lib, self.state.scan)
        self.list.clear()
        for i in self._issues:
            item = QListWidgetItem(f'[{tr(_LEVEL_TEXT[i.level])}]  {i.message}')
            item.setForeground(QColor(theme.T[_LEVEL_COLOR[i.level]]))
            self.list.addItem(item)
        errors = sum(1 for i in self._issues if i.level == checks.ERROR)
        warns = sum(1 for i in self._issues if i.level == checks.WARNING)
        if errors:
            text, level = tr('エラー {n} 件 — 直すまで書き出せません', n=errors), 'error'
        elif warns:
            text, level = tr('注意 {n} 件 — 書き出せます', n=warns), 'warning'
        else:
            text, level = tr('問題なし'), 'ok'
            if not self._issues:
                self.list.addItem(tr('問題は見つかりませんでした。'))
        self.pill.setText(text)
        self.pill.setProperty('level', level)
        repolish(self.pill)
        self.export_btn.setEnabled(not errors)
        self._update_target()

    def _update_target(self) -> None:
        out = self.out_edit.text().strip()
        name = self.state.project.effective_resource_name()
        self.target_label.setText(tr('保存先: {path}', path=str(Path(out) / name)) if out and name else '')

    def _on_slot(self, *_args) -> None:
        if self._loading:
            return
        auto = self.slot_auto.isChecked()
        self.slot.setEnabled(not auto)
        self.state.project.slot_order = None if auto else self.slot.value()
        self.state.touch()

    def browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr('書き出し先のフォルダを選ぶ'), self.out_edit.text())
        if d:
            self.out_edit.setText(d)

    def export(self) -> None:
        self.refresh()
        if checks.has_errors(self._issues):
            return
        p = self.state.project
        out = self.out_edit.text().strip()
        if not out or not Path(out).is_dir():
            QMessageBox.warning(self, tr('書き出し'), tr('書き出し先のフォルダを選んでください。'))
            return
        target = Path(out) / p.effective_resource_name()
        overwrite = False
        if target.exists():
            ans = QMessageBox.question(self, tr('書き出し'),
                                       tr('{path} は既にあります。中身を今回の書き出しで置き換えますか?', path=str(target)))
            if ans != QMessageBox.StandardButton.Yes:
                return
            overwrite = True
        took_slot = False
        if p.slot_order is None:
            # ここで決めた番号はプロジェクトに残す(書き出し直しても並び順が変わらないように)
            p.slot_order = self.state.settings.take_slot()
            took_slot = True
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            done, res = exporter.export_build(p, self.state.lib, self.state.scan.assets, out, overwrite=overwrite)
        except (exporter.ExportError, MetaError, OSError) as e:
            QGuiApplication.restoreOverrideCursor()
            if took_slot:
                p.slot_order = None
            QMessageBox.critical(self, tr('書き出し'), tr('書き出せませんでした。\n{reason}', reason=str(e)))
            return
        except BaseException:
            QGuiApplication.restoreOverrideCursor()
            raise
        QGuiApplication.restoreOverrideCursor()
        self.state.settings['last_export_dir'] = out
        self._last_target = done
        text = tr('書き出しました: {path}(ファイル {n} 個)', path=str(done), n=len(res.files) + len(res.assets))
        if res.skipped_fields:
            text += '\n' + tr('テンプレートに無いため書かなかった項目: {tags}', tags=', '.join(res.skipped_fields))
        stale = exporter.stale_dirs(out, done.name)
        if stale:
            text += '\n' + tr('作業用フォルダが消し残っています。手で削除してください: {names}',
                              names=', '.join(s.name for s in stale))
        if took_slot:
            self.load_slot_only()
            self.state.touch()
        self.refresh()
        self.result.setText(text)
        self.open_btn.show()

    def load_slot_only(self) -> None:
        p = self.state.project
        self._loading = True
        try:
            self.slot_auto.setChecked(p.slot_order is None)
            self.slot.setEnabled(p.slot_order is not None)
            self.slot.setValue(p.slot_order if p.slot_order is not None else int(self.state.settings['next_slot']))
        finally:
            self._loading = False

    def _open_target(self) -> None:
        if self._last_target is not None and self._last_target.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_target)))
