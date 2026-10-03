"""設定: 言語・配色・次に使う並び順の番号。"""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QVBoxLayout

from .. import i18n
from ..i18n import N_, tr
from ..settings import LANGUAGES, THEMES, Settings
from . import theme
from .widgets import NoWheelComboBox, label

_THEME_NAMES = {'system': N_('システムに合わせる'), 'dark': N_('ダーク'), 'light': N_('ライト')}


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(tr('設定'))
        self.setMinimumWidth(420)

        self.lang = NoWheelComboBox()
        for code in LANGUAGES:
            if code:
                self.lang.addItem(i18n.LANG_NAMES[code], code)
            else:
                name = i18n.LANG_NAMES[i18n.system_language()]
                self.lang.addItem(tr('OS の言語に合わせる({name})', name=name), code)
        self.lang.setCurrentIndex(max(0, LANGUAGES.index(settings['language'])))

        self.theme = NoWheelComboBox()
        for t in THEMES:
            self.theme.addItem(tr(_THEME_NAMES[t]), t)
        self.theme.setCurrentIndex(max(0, THEMES.index(settings['theme'])))
        self.theme.currentIndexChanged.connect(self._preview_theme)

        self.slot = QSpinBox()
        self.slot.setRange(1, 99999)
        self.slot.setValue(int(settings['next_slot']))
        self.slot.setToolTip(tr('並び順を自動で決めるときに、次に使う番号。ほかのツールで作った武器と重なるときに変えてください。'))

        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.addRow(tr('言語'), self.lang)
        form.addRow('', label(tr('言語の変更は、次に起動したときに反映されます。'), 'faint', wrap=True))
        form.addRow(tr('配色'), self.theme)
        form.addRow(tr('次に使う並び順の番号'), self.slot)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.addLayout(form)
        root.addSpacing(8)
        root.addWidget(buttons)

    def _preview_theme(self) -> None:
        theme.apply(self.theme.currentData(), i18n.current())

    def accept(self) -> None:
        self.settings['language'] = self.lang.currentData()
        self.settings['theme'] = self.theme.currentData()
        self.settings['next_slot'] = self.slot.value()
        super().accept()

    def reject(self) -> None:
        theme.apply(self.settings['theme'], i18n.current())     # 試し見した配色を元へ戻す
        super().reject()
