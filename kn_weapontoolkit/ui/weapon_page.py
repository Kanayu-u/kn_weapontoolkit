"""1. 武器: モデルのフォルダ・テンプレート・名前。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QSpinBox,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import assets, suggest
from ..i18n import tr
from ..model import sanitize_resource_name
from . import theme
from .state import AppState
from .widgets import NoWheelComboBox, card, label, page_header, set_combo_text


class WeaponPage(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.setObjectName('page')
        self.state = state
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(page_header(tr('武器'), tr('モデルのフォルダを選び、元にするバニラ武器(テンプレート)と名前を決めます。')))

        # --- フォルダ
        self.dir_edit = QLineEdit()
        self.dir_edit.setReadOnly(True)
        self.dir_edit.setPlaceholderText(tr('モデル(.ydr)とテクスチャ(.ytd)の入ったフォルダ。ここへドロップしても選べます'))
        browse = QPushButton(tr('参照…'))
        browse.clicked.connect(self.browse)
        reload_btn = QPushButton(tr('読み直す'))
        reload_btn.clicked.connect(self.state.rescan)
        row = QHBoxLayout()
        row.addWidget(label(tr('モデルのフォルダ')))
        row.addWidget(self.dir_edit, 1)
        row.addWidget(browse)
        row.addWidget(reload_btn)
        root.addWidget(card(row))

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # --- 見つかったファイル
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([tr('ファイル'), tr('用途')])
        self.tree.setColumnWidth(0, 300)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.count_label = label('', 'faint')
        left = QVBoxLayout()
        left.addWidget(label(tr('見つかったファイル'), 'h2'))
        left.addWidget(self.tree, 1)
        left.addWidget(self.count_label)
        body.addLayout(left, 3)

        # --- 基本項目
        self.template = NoWheelComboBox()
        self.template.addItems(state.lib.weapon_names())
        self.template.activated.connect(self._on_template)
        self.display_name = QLineEdit()
        self.display_name.setToolTip(tr('ゲーム内に表示される武器の名前。'))
        self.display_name.textEdited.connect(self._on_edit)
        self.weapon_id = QLineEdit()
        self.weapon_id.setToolTip(tr('スクリプトから武器を指す名前。WEAPON_ で始まる大文字の英数字。'))
        self.weapon_id.textEdited.connect(self._on_id_edited)
        self.model = NoWheelComboBox()
        self.model.setEditable(True)
        self.model.setInsertPolicy(NoWheelComboBox.InsertPolicy.NoInsert)
        self.model.setToolTip(tr('武器本体のモデル名(.ydr の拡張子なし)。'))
        self.model.editTextChanged.connect(self._on_edit)
        self.resource = QLineEdit()
        self.resource.setToolTip(tr('書き出すリソースのフォルダ名。空なら武器 ID を小文字にしたものを使います。'))
        self.resource.textEdited.connect(self._on_edit)
        self.lod = QSpinBox()
        self.lod.setRange(1, 10000)
        self.lod.setToolTip(tr('この距離より遠いと武器モデルを描きません。'))
        self.lod.valueChanged.connect(self._on_edit)

        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.addRow(tr('テンプレート'), self.template)
        form.addRow(tr('表示名'), self.display_name)
        form.addRow(tr('武器 ID'), self.weapon_id)
        form.addRow(tr('モデル名'), self.model)
        form.addRow(tr('リソース名'), self.resource)
        form.addRow(tr('LOD 距離'), self.lod)
        self.template_note = label('', 'faint', wrap=True)
        right = QVBoxLayout()
        right.addWidget(label(tr('基本'), 'h2'))
        right.addWidget(card(form))
        right.addWidget(self.template_note)
        right.addStretch(1)
        body.addLayout(right, 2)

        state.project_replaced.connect(self.load)
        state.templates_changed.connect(self._reload_templates)
        state.template_changed.connect(self._update_template_note)
        state.assets_changed.connect(self._on_assets)
        state.changed.connect(self.refresh_files)
        theme.notifier().changed.connect(lambda _m: self.refresh_files(force=True))
        self.load()

    # --- 入力欄 ← プロジェクト
    def load(self) -> None:
        p = self.state.project
        self._loading = True
        try:
            self.dir_edit.setText(p.import_dir)
            set_combo_text(self.template, p.template)
            self.display_name.setText(p.display_name)
            self.weapon_id.setText(p.weapon_id)
            self._fill_models()
            self.resource.setText(p.resource_name)
            self.lod.setValue(p.lod)
            self._update_placeholders()
        finally:
            self._loading = False
        self._update_template_note()
        self.refresh_files(force=True)

    def _reload_templates(self) -> None:
        self._loading = True
        try:
            self.template.clear()
            self.template.addItems(self.state.lib.weapon_names())
            set_combo_text(self.template, self.state.project.template)
        finally:
            self._loading = False
        self._update_template_note()

    def _update_template_note(self) -> None:
        tpl = self.state.template()
        notes = []
        if tpl is not None:
            if tpl.source == 'user':
                notes.append(tr('取り込んだテンプレートです。'))
            donors = {tpl.borrowed('animations'), tpl.borrowed('personality')} - {''}
            if donors:
                notes.append(tr('動作と構え方は {names} のものを借りています。持ち方がバニラと違って見えることがあります。',
                                names=', '.join(sorted(donors))))
        self.template_note.setText(' '.join(notes))

    def _fill_models(self) -> None:
        was = self._loading
        self._loading = True
        try:
            self.model.clear()
            self.model.addItems(sorted({n.lower() for n in suggest.base_models(self.state.scan.assets)}))
            set_combo_text(self.model, self.state.project.model)
        finally:
            self._loading = was

    def _update_placeholders(self) -> None:
        self.resource.setPlaceholderText(sanitize_resource_name(self.weapon_id.text()))

    # --- 入力欄 → プロジェクト
    def _on_id_edited(self, text: str) -> None:
        up = text.upper().replace(' ', '_')
        if up != text:
            pos = self.weapon_id.cursorPosition()
            self.weapon_id.setText(up)
            self.weapon_id.setCursorPosition(pos)
        self._on_edit()

    def _on_edit(self, *_args) -> None:
        if self._loading:
            return
        p = self.state.project
        p.display_name = self.display_name.text()
        p.weapon_id = self.weapon_id.text().strip()
        p.model = self.model.currentText().strip().lower()
        p.resource_name = self.resource.text().strip()
        p.lod = self.lod.value()
        self._update_placeholders()
        self.state.touch()

    def _on_template(self, _index: int) -> None:
        if self._loading:
            return
        p = self.state.project
        new = self.template.currentText()
        if new == p.template:
            return
        if p.fields:
            ans = QMessageBox.question(self, tr('テンプレートの変更'),
                                       tr('テンプレートを変えると「性能」で変更した値は破棄されます。続けますか?'))
            if ans != QMessageBox.StandardButton.Yes:
                self._loading = True
                set_combo_text(self.template, p.template)
                self._loading = False
                return
        old = self.state.template()
        p.template = new
        p.fields = {}
        tpl = self.state.template()
        # モデル名がまだテンプレートのまま(=未設定)なら、新しいテンプレートのモデル名に合わせる
        if tpl is not None and (not p.model or (old is not None and p.model == old.model.lower())):
            guess = suggest.guess_weapon_model(self.state.scan.assets)
            p.model = guess or tpl.model.lower()
            self._fill_models()
        self.state.template_changed.emit()
        self.state.touch()

    def browse(self) -> None:
        start = self.state.project.import_dir or self.state.settings['last_import_dir']
        d = QFileDialog.getExistingDirectory(self, tr('モデルのフォルダを選ぶ'), start)
        if d:
            self.set_import_dir(d)

    def set_import_dir(self, d: str) -> None:
        self.state.project.import_dir = d
        self.state.settings['last_import_dir'] = d
        self.dir_edit.setText(d)
        self.state.scan = assets.scan(d)
        # 今のモデル名のファイルが無ければ、ファイル名から武器本体を推測して入れる。
        # フォルダを選び直したときだけ行う(プロジェクトを開いただけで中身を書き換えない)
        p = self.state.project
        found = self.state.scan.assets
        if found and f'{p.model.lower()}.ydr' not in {a.key for a in found}:
            guess = suggest.guess_weapon_model(found)
            if guess:
                p.model = guess
        self.state.assets_changed.emit()
        self.state.touch()

    def _on_assets(self) -> None:
        self._fill_models()
        self.refresh_files(force=True)

    # --- ファイル一覧
    def refresh_files(self, force: bool = False) -> None:
        if self._skip_refresh:
            return
        p = self.state.project
        scan = self.state.scan
        model = p.model.strip().lower()
        comp_by_model = {c.model.strip().lower(): c.name for c in p.components if c.model}
        excluded = set(p.excluded_assets)
        # 入力のたびに呼ばれるので、「用途」の列に関わる値が変わっていなければ作り直さない
        signature = (model, tuple(sorted(comp_by_model.items())), bool(p.import_dir))
        if not force and signature == self._signature:
            return
        self._signature = signature
        self._loading_tree = True
        try:
            self.tree.clear()
            for a in scan.assets:
                if a.base == model and a.ext in ('.ydr', '.ytd'):
                    role, color = tr('武器本体'), theme.T['ok']
                elif a.base in comp_by_model and a.ext in ('.ydr', '.ytd'):
                    role, color = comp_by_model[a.base], theme.T['accent']
                elif a.ext in ('.ydr', '.ytd'):
                    role, color = tr('未割り当て'), theme.T['warn']
                else:
                    role, color = '', theme.T['muted']
                it = QTreeWidgetItem([a.name, role])
                it.setData(0, Qt.ItemDataRole.UserRole, a.key)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(0, Qt.CheckState.Unchecked if a.key in excluded else Qt.CheckState.Checked)
                it.setForeground(1, QColor(color))
                it.setToolTip(0, str(a.path))
                self.tree.addTopLevelItem(it)
        finally:
            self._loading_tree = False
        if not p.import_dir:
            self.count_label.setText(tr('フォルダが選ばれていません。'))
        elif not scan.assets:
            self.count_label.setText(tr('このフォルダには .ydr / .ytd がありません。'))
        else:
            self.count_label.setText(tr('{n} 個。チェックを外したファイルは書き出しません。', n=len(scan.assets)))

    _loading_tree = False
    _skip_refresh = False
    _signature: tuple | None = None

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._loading_tree or column != 0:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        ex = set(self.state.project.excluded_assets)
        if item.checkState(0) == Qt.CheckState.Checked:
            ex.discard(key)
        else:
            ex.add(key)
        self.state.project.excluded_assets = sorted(ex)
        # チェックの切り替えでは一覧を作り直さない(処理中の項目を消すことになり、選択位置も飛ぶ)
        self._skip_refresh = True
        try:
            self.state.touch()
        finally:
            self._skip_refresh = False
