"""2. 性能: weapons.meta の値。主な項目のフォームと、全項目の一覧表は同じ値を編集する。"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QScrollArea,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..fieldinfo import BASIC_FIELDS
from ..i18n import tr
from . import theme
from .state import AppState
from .widgets import NoWheelComboBox, card, label, page_header, repolish, set_combo_text


class StatsPage(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.setObjectName('page')
        self.state = state
        self._loading = False
        self._editors: dict[str, tuple[QLabel, QWidget]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        head = QHBoxLayout()
        head.addWidget(page_header(tr('性能'), tr('テンプレートの値から変えたい項目だけ書き換えます。変えた項目は色が付きます。')), 1)
        self.reset_btn = QPushButton(tr('すべてテンプレートの値に戻す'))
        self.reset_btn.clicked.connect(self.reset_all)
        head.addWidget(self.reset_btn, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # --- 主な項目
        self.basic_host = QWidget()
        self.basic_grid = QGridLayout(self.basic_host)
        self.basic_grid.setContentsMargins(0, 0, 16, 0)
        self.basic_grid.setVerticalSpacing(8)
        self.basic_grid.setColumnStretch(1, 1)
        scroll = QScrollArea()
        scroll.setObjectName('plain')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.basic_host)
        self.fire_rate = QLineEdit()
        self.fire_rate.setPlaceholderText(tr('テンプレートのまま'))
        self.fire_rate.setToolTip(tr('射撃動作の再生速度(weaponanimations.meta の AnimFireRateModifier)。1.0 が標準。小さいほど連射が遅く、大きいほど速くなる。空ならテンプレートの値のまま。'))
        self.fire_rate.textEdited.connect(self._on_fire_rate)
        fr = QHBoxLayout()
        fr.addWidget(label(tr('射撃動作の速度倍率')))
        fr.addWidget(self.fire_rate, 1)
        left = QVBoxLayout()
        left.addWidget(label(tr('主な項目'), 'h2'))
        inner = QVBoxLayout()
        inner.addWidget(scroll, 1)
        left.addWidget(card(inner), 1)
        left.addWidget(card(fr))
        body.addLayout(left, 5)

        # --- すべての項目
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr('項目名で絞り込み'))
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([tr('項目'), tr('値'), tr('テンプレートの値')])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 130)
        self.table.cellChanged.connect(self._on_cell)
        right = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(label(tr('すべての項目'), 'h2'))
        top.addStretch(1)
        top.addWidget(self.filter, 2)
        right.addLayout(top)
        right.addWidget(self.table, 1)
        body.addLayout(right, 6)

        state.project_replaced.connect(self.rebuild)
        state.template_changed.connect(self.rebuild)
        theme.notifier().changed.connect(lambda _m: self.refresh_values())
        self.rebuild()

    # --- 組み立て
    def rebuild(self) -> None:
        tpl = self.state.template()
        self._loading = True
        try:
            while self.basic_grid.count():
                w = self.basic_grid.takeAt(0).widget()
                if w is not None:
                    w.setParent(None)   # deleteLater だけだと、消えるまで前のテンプレートの欄が重なって見える
                    w.deleteLater()
            self._editors.clear()
            self.table.setRowCount(0)
            if tpl is None:
                self.basic_grid.addWidget(label(tr('テンプレートを読めません。'), 'errText'), 0, 0)
                return
            row = 0
            for tag, name, tip, choices in BASIC_FIELDS:
                f = tpl.field(tag)
                if f is None:
                    continue
                lb = QLabel(tr(name))
                lb.setObjectName('fieldLabel')
                lb.setToolTip(f'{tr(tip)}\n<{tag}>')
                if choices is not None:
                    ed = NoWheelComboBox()
                    ed.setEditable(True)
                    ed.setInsertPolicy(NoWheelComboBox.InsertPolicy.NoInsert)
                    ed.addItems(choices)
                    ed.editTextChanged.connect(lambda text, t=tag, e=ed: self._set(t, text, e))
                else:
                    ed = QLineEdit()
                    ed.textEdited.connect(lambda text, t=tag, e=ed: self._set(t, text, e))
                ed.setToolTip(lb.toolTip())
                self.basic_grid.addWidget(lb, row, 0)
                self.basic_grid.addWidget(ed, row, 1)
                self._editors[tag] = (lb, ed)
                row += 1
            self.basic_grid.setRowStretch(row, 1)

            self.table.setRowCount(len(tpl.fields))
            for r, f in enumerate(tpl.fields):
                name = QTableWidgetItem(f.tag)
                name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                base = QTableWidgetItem(f.value)
                base.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(r, 0, name)
                self.table.setItem(r, 1, QTableWidgetItem(''))
                self.table.setItem(r, 2, base)
        finally:
            self._loading = False
        self.refresh_values()
        self._apply_filter(self.filter.text())

    # --- 値の表示
    def refresh_values(self, skip: QWidget | None = None, restyle: bool = True) -> None:
        """入力欄と表をプロジェクトの値に合わせる。restyle=False なら、変更の有無が変わった行だけ色を付け直す。"""
        tpl = self.state.template()
        if tpl is None:
            return
        p = self.state.project
        self._loading = True
        try:
            for tag, (lb, ed) in self._editors.items():
                f = tpl.field(tag)
                value = p.fields.get(tag, f.value)
                if ed is not skip:
                    if isinstance(ed, QLineEdit):
                        if ed.text() != value:
                            ed.setText(value)
                    elif ed.currentText() != value:
                        set_combo_text(ed, value)
                changed = tag in p.fields
                if lb.property('changed') != changed:
                    lb.setProperty('changed', changed)
                    repolish(lb)
            accent = QColor(theme.T['accent'])
            normal = QColor(theme.T['text'])
            muted = QColor(theme.T['muted'])
            for r, f in enumerate(tpl.fields):
                item = self.table.item(r, 1)
                value = p.fields.get(f.tag, f.value)
                if item.text() != value and self.table is not skip:
                    item.setText(value)
                changed = f.tag in p.fields
                if not restyle and item.data(Qt.ItemDataRole.UserRole) == changed:
                    continue
                item.setData(Qt.ItemDataRole.UserRole, changed)
                font = QFont(item.font())
                font.setBold(changed)
                item.setFont(font)
                item.setForeground(accent if changed else normal)
                self.table.item(r, 0).setForeground(accent if changed else normal)
                self.table.item(r, 2).setForeground(muted)
            if self.fire_rate is not skip:
                self.fire_rate.setText('' if p.fire_rate is None else f'{p.fire_rate:g}')
                self._mark_fire_rate(False)
            self.reset_btn.setEnabled(bool(p.fields) or p.fire_rate is not None)
        finally:
            self._loading = False

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for r in range(self.table.rowCount()):
            self.table.setRowHidden(r, bool(needle) and needle not in self.table.item(r, 0).text().lower())

    # --- 編集
    def _set(self, tag: str, value: str, source: QWidget | None = None) -> None:
        if self._loading:
            return
        tpl = self.state.template()
        f = tpl.field(tag) if tpl is not None else None
        if f is None:
            return
        value = value.strip()
        p = self.state.project
        if value == f.value:
            p.fields.pop(tag, None)     # テンプレートと同じ値は保存しない
        else:
            p.fields[tag] = value
        self.refresh_values(skip=source, restyle=False)     # 入力中の欄(source)は書き戻さない(カーソルが飛ぶ)
        self.state.touch()

    def _on_cell(self, row: int, column: int) -> None:
        if self._loading or column != 1:
            return
        self._set(self.table.item(row, 0).text(), self.table.item(row, 1).text(), source=self.table)

    def _on_fire_rate(self, text: str) -> None:
        if self._loading:
            return
        text = text.strip()
        try:
            value = float(text) if text else None
        except ValueError:
            value = math.nan
        if value is not None and not (math.isfinite(value) and value > 0):
            self._mark_fire_rate(True)      # 数値でない間は前の値のまま。欄を赤くして確定していないことを示す
            return
        self._mark_fire_rate(False)
        self.state.project.fire_rate = value
        self.reset_btn.setEnabled(bool(self.state.project.fields) or self.state.project.fire_rate is not None)
        self.state.touch()

    def _mark_fire_rate(self, invalid: bool) -> None:
        if bool(self.fire_rate.property('invalid')) != invalid:
            self.fire_rate.setProperty('invalid', invalid)
            repolish(self.fire_rate)

    def reset_all(self) -> None:
        self.state.project.fields = {}
        self.state.project.fire_rate = None
        self.refresh_values()
        self.state.touch()
