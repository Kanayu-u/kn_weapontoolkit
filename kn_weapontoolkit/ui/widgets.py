"""小さな部品。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QLayout, QVBoxLayout, QWidget


def label(text: str, name: str = '', wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def card(layout: QLayout) -> QFrame:
    f = QFrame()
    f.setObjectName('card')
    layout.setContentsMargins(16, 14, 16, 14)
    f.setLayout(layout)
    return f


def page_header(title: str, sub: str) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 4)
    v.setSpacing(2)
    v.addWidget(label(title, 'h1'))
    v.addWidget(label(sub, 'muted', wrap=True))
    return w


def repolish(w: QWidget) -> None:
    """動的プロパティを変えたあと、QSS を当て直す。"""
    w.style().unpolish(w)
    w.style().polish(w)


class NoWheelComboBox(QComboBox):
    """スクロール中に値が変わってしまわないよう、フォーカスが無いときはホイールを無視する。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMaxVisibleItems(18)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


def set_combo_text(combo: QComboBox, text: str) -> None:
    """候補にあれば選び、無ければ(編集可のとき)そのまま文字として入れる。"""
    i = combo.findText(text, Qt.MatchFlag.MatchFixedString)
    if i >= 0:
        combo.setCurrentIndex(i)
    elif combo.isEditable():
        combo.setCurrentIndex(-1)
        combo.setEditText(text)
