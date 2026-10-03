"""3. コンポーネント: マガジン・サプレッサーなどの部品。一覧の並びは project.components と常に同じ順。"""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QFormLayout, QHBoxLayout, QLineEdit, QListWidget, QMessageBox, QPushButton,
                               QSpinBox, QVBoxLayout, QWidget)

from .. import exporter, suggest
from ..gamedata import CLIP_AMMO_INFOS
from ..i18n import tr
from ..model import ComponentSpec
from ..templates import KNOWN_BONES, ComponentTemplate
from ..xmlio import MetaError
from .state import AppState
from .widgets import NoWheelComboBox, card, label, page_header, set_combo_text


class ComponentsPage(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.setObjectName('page')
        self.state = state
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(page_header(tr('コンポーネント'), tr('マガジンやサプレッサーなど、武器に付ける部品を定義します。無くても書き出せます。')))

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # --- 一覧
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.currentRowChanged.connect(self._on_select)
        add = QPushButton(tr('追加'))
        add.clicked.connect(self.add)
        self.remove_btn = QPushButton(tr('削除'))
        self.remove_btn.setObjectName('danger')
        self.remove_btn.clicked.connect(self.remove)
        detect = QPushButton(tr('ファイルから自動検出'))
        detect.setToolTip(tr('武器モデル名で始まる部品モデル(_mag1 / _supp / _scope など)からコンポーネントを作ります。'))
        detect.clicked.connect(self.detect)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(self.remove_btn)
        buttons.addStretch(1)
        buttons.addWidget(detect)
        self.keep = QCheckBox(tr('テンプレートに元からある部品を残す'))
        self.keep.setToolTip(tr('テンプレート武器が持つバニラの部品定義を残します。同じボーンに部品を追加した場合は、追加した方に置き換わります。'))
        self.keep.toggled.connect(self._on_keep)
        self.tpl_info = label('', 'faint', wrap=True)
        left = QVBoxLayout()
        left.addWidget(self.list, 1)
        left.addLayout(buttons)
        left.addWidget(self.keep)
        left.addWidget(self.tpl_info)
        body.addLayout(left, 4)

        # --- 詳細
        self.template = NoWheelComboBox()
        self.template.addItems(state.lib.component_names())
        self.template.activated.connect(self._on_template)
        self.name = QLineEdit()
        self.name.setToolTip(tr('スクリプトから部品を指す名前。COMPONENT_ で始まる大文字の英数字。バニラと同じ名前は避けてください。'))
        self.name.textEdited.connect(self._on_name_edited)
        self.model = NoWheelComboBox()
        self.model.setEditable(True)
        self.model.setInsertPolicy(NoWheelComboBox.InsertPolicy.NoInsert)
        self.model.setToolTip(tr('部品のモデル名(.ydr の拡張子なし)。'))
        self.model.editTextChanged.connect(self._on_edit)
        self.lod = QSpinBox()
        self.lod.setRange(1, 10000)
        self.lod.valueChanged.connect(self._on_edit)
        self.clip = QSpinBox()
        self.clip.setRange(1, 99999)
        self.clip.valueChanged.connect(self._on_edit)
        self.ammo = NoWheelComboBox()
        self.ammo.setEditable(True)
        self.ammo.setInsertPolicy(NoWheelComboBox.InsertPolicy.NoInsert)
        self.ammo.addItems(CLIP_AMMO_INFOS)
        self.ammo.lineEdit().setPlaceholderText(tr('武器の弾薬のまま'))
        self.ammo.setToolTip(tr('このマガジンを付けたときだけ使う弾薬(曳光弾など)。空なら武器の弾薬のまま。'))
        self.ammo.editTextChanged.connect(self._on_edit)
        self.bone = NoWheelComboBox()
        self.bone.setEditable(True)
        self.bone.setInsertPolicy(NoWheelComboBox.InsertPolicy.NoInsert)
        self.bone.addItems(KNOWN_BONES)
        self.bone.setToolTip(tr('部品を取り付ける武器モデル側のボーン。空ならテンプレートから自動で決めます。'))
        self.bone.editTextChanged.connect(self._on_edit)
        self.default = QCheckBox(tr('最初から装着しておく'))
        self.default.setToolTip(tr('武器を手に入れた時点で付いている部品にします。マガジンは通常1つをこれにします。'))
        self.default.toggled.connect(self._on_edit)

        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.addRow(tr('テンプレート'), self.template)
        form.addRow(tr('コンポーネント名'), self.name)
        form.addRow(tr('モデル名'), self.model)
        form.addRow(tr('LOD 距離'), self.lod)
        form.addRow(tr('装弾数'), self.clip)
        form.addRow(tr('弾薬'), self.ammo)
        form.addRow(tr('取り付けボーン'), self.bone)
        form.addRow('', self.default)
        self.form_card = card(form)
        self.hint = label('', 'faint', wrap=True)
        right = QVBoxLayout()
        right.addWidget(self.form_card)
        right.addWidget(self.hint)
        right.addStretch(1)
        body.addLayout(right, 5)

        state.project_replaced.connect(self.load)
        state.template_changed.connect(self._update_template_info)
        state.assets_changed.connect(self._fill_models)
        state.templates_changed.connect(self._reload_templates)
        state.template_changed.connect(lambda: self._show(self.current()))
        self.load()

    # --- 表示
    def current(self) -> ComponentSpec | None:
        i = self.list.currentRow()
        comps = self.state.project.components
        return comps[i] if 0 <= i < len(comps) else None

    def _template_of(self, spec: ComponentSpec) -> ComponentTemplate | None:
        try:
            return self.state.lib.component(spec.template)
        except MetaError:
            return None

    def load(self) -> None:
        self._loading = True
        try:
            self.list.clear()
            for c in self.state.project.components:
                self.list.addItem(c.name or c.template)
            self.keep.setChecked(self.state.project.keep_template_attachments)
        finally:
            self._loading = False
        self._fill_models()
        self._update_template_info()
        self.list.setCurrentRow(0 if self.state.project.components else -1)
        self._show(self.current())

    def _reload_templates(self) -> None:
        self._loading = True
        try:
            self.template.clear()
            self.template.addItems(self.state.lib.component_names())
        finally:
            self._loading = False
        self._update_template_info()
        self._show(self.current())

    def _fill_models(self) -> None:
        was = self._loading
        self._loading = True
        try:
            text = self.model.currentText()
            self.model.clear()
            self.model.addItems(sorted({n.lower() for n in suggest.base_models(self.state.scan.assets)}))
            set_combo_text(self.model, text)
        finally:
            self._loading = was

    def _update_template_info(self) -> None:
        tpl = self.state.template()
        if tpl is None or not tpl.attach_points:
            self.keep.setEnabled(False)
            self.tpl_info.setText(tr('このテンプレートに元からある部品はありません。'))
            return
        self.keep.setEnabled(True)
        parts = [f'{bone}: {", ".join(names)}' for bone, names in tpl.attach_points]
        self.tpl_info.setText(tr('テンプレートの部品 — {list}', list=' / '.join(parts)))

    def _show(self, spec: ComponentSpec | None) -> None:
        self._loading = True
        try:
            self.form_card.setEnabled(spec is not None)
            self.remove_btn.setEnabled(spec is not None)
            if spec is None:
                self.name.setText('')
                self.model.setEditText('')
                self.hint.setText(tr('「追加」または「ファイルから自動検出」で部品を作ります。'))
                return
            ct = self._template_of(spec)
            set_combo_text(self.template, spec.template)
            self.name.setText(spec.name)
            set_combo_text(self.model, spec.model)
            self.lod.setValue(spec.lod)
            is_clip = ct is not None and ct.is_clip
            self.clip.setEnabled(is_clip)
            self.clip.setValue(spec.clip_size if spec.clip_size else (ct.clip_size if is_clip and ct.clip_size else 1))
            self.ammo.setEnabled(ct is not None and ct.has_ammo_info)
            set_combo_text(self.ammo, spec.ammo_info)
            set_combo_text(self.bone, spec.bone)
            auto = exporter.component_bone(ComponentSpec(), ct, self.state.template()) if ct is not None else ''
            self.bone.lineEdit().setPlaceholderText(tr('自動: {bone}', bone=auto) if auto else tr('ボーン名を入力'))
            self.default.setChecked(spec.default)
            if ct is None:
                self.hint.setText(tr('テンプレート {name} を読めません。', name=spec.template))
            elif is_clip and not ct.has_ammo_info:
                self.hint.setText(tr('このテンプレートは弾薬の切り替えに対応していません。'))
            else:
                self.hint.setText('')
        finally:
            self._loading = False

    def _on_select(self, _row: int) -> None:
        if not self._loading:
            self._show(self.current())

    # --- 編集
    def _taken(self, but: ComponentSpec | None = None) -> set[str]:
        return {c.name.upper() for c in self.state.project.components if c is not but}

    def add(self) -> None:
        p = self.state.project
        short = p.template.removeprefix('WEAPON_')
        names = self.state.lib.component_names()
        # 既定は、その武器のマガジン(あれば)。2個目以降は CLIP_02 …と進める
        clips = [n for n in names if n.startswith(f'COMPONENT_{short}_CLIP_')]
        used = {c.template for c in p.components}
        # マガジンが尽きたら(または元から無い武器なら)汎用の部品(COMPONENT_AT_…)から、まだ使っていないもの
        generic = [n for n in names if n.startswith('COMPONENT_AT_')]
        tpl = (next((n for n in clips if n not in used), None) or next((n for n in generic if n not in used), None)
               or (names[0] if names else ''))
        if not tpl:
            QMessageBox.warning(self, tr('コンポーネント'), tr('コンポーネントのテンプレートがありません。'))
            return
        spec = self._new_spec(tpl)
        p.components.append(spec)
        self.list.addItem(spec.name)
        self.list.setCurrentRow(len(p.components) - 1)
        self.state.touch()

    def _new_spec(self, tpl_name: str) -> ComponentSpec:
        p = self.state.project
        spec = ComponentSpec(template=tpl_name, name=suggest.auto_component_name(p.weapon_id, tpl_name, self._taken()))
        try:
            ct = self.state.lib.component(tpl_name)
        except MetaError:
            return spec
        spec.model = ct.model.lower()
        spec.clip_size = ct.clip_size
        if ct.is_clip and not any(c.default and c.clip_size is not None for c in p.components):
            spec.default = True
        return spec

    def remove(self) -> None:
        i = self.list.currentRow()
        comps = self.state.project.components
        if not 0 <= i < len(comps):
            return
        del comps[i]
        self._loading = True
        self.list.takeItem(i)
        self._loading = False
        self.list.setCurrentRow(min(i, len(comps) - 1))
        self._show(self.current())
        self.state.touch()

    def detect(self) -> None:
        p = self.state.project
        found = suggest.suggest_components(p, self.state.lib, self.state.scan.assets)
        if not found:
            QMessageBox.information(self, tr('自動検出'),
                                    tr('新しく追加できる部品モデルは見つかりませんでした。\n武器モデル名({model})で始まる _mag1 / _mag2 / _supp / _scope / _afgrip / _flsh を探します。',
                                       model=p.model or '?'))
            return
        for spec in found:
            p.components.append(spec)
            self.list.addItem(spec.name)
        self.list.setCurrentRow(len(p.components) - len(found))
        self.state.touch()

    def _on_template(self, _index: int) -> None:
        spec = self.current()
        if self._loading or spec is None:
            return
        new = self.template.currentText()
        if new == spec.template:
            return
        p = self.state.project
        old_ct = self._template_of(spec)
        old_auto = suggest.auto_component_name(p.weapon_id, spec.template)
        # 名前とモデルは、手で直していなければ新しいテンプレートに合わせる
        if not spec.name or spec.name.upper().startswith(old_auto):
            spec.name = suggest.auto_component_name(p.weapon_id, new, self._taken(spec))
        spec.template = new
        ct = self._template_of(spec)
        if ct is not None:
            if not spec.model or (old_ct is not None and spec.model == old_ct.model.lower()):
                spec.model = ct.model.lower()
            spec.clip_size = ct.clip_size
            if not ct.has_ammo_info:
                spec.ammo_info = ''
        spec.bone = ''
        self.list.currentItem().setText(spec.name or spec.template)
        self._show(spec)
        self.state.touch()

    def _on_name_edited(self, text: str) -> None:
        up = text.upper().replace(' ', '_')
        if up != text:
            pos = self.name.cursorPosition()
            self.name.setText(up)
            self.name.setCursorPosition(pos)
        self._on_edit()

    def _on_edit(self, *_args) -> None:
        spec = self.current()
        if self._loading or spec is None:
            return
        spec.name = self.name.text().strip()
        spec.model = self.model.currentText().strip().lower()
        spec.lod = self.lod.value()
        if self.clip.isEnabled():
            spec.clip_size = self.clip.value()
        spec.ammo_info = self.ammo.currentText().strip() if self.ammo.isEnabled() else ''
        spec.bone = self.bone.currentText().strip()
        spec.default = self.default.isChecked()
        self.list.currentItem().setText(spec.name or spec.template)
        self.state.touch()

    def _on_keep(self, on: bool) -> None:
        if self._loading:
            return
        self.state.project.keep_template_attachments = on
        self.state.touch()
