"""ホイールを押したまま上下に動かすと、カーソルの下の一覧を送る。アプリ全体に 1 つ入れる。"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea, QApplication, QWidget

from ..autoscroll import Accumulator, step


def find_area(widget: QWidget | None) -> QAbstractScrollArea | None:
    """widget から親へたどり、縦に送れる欄を返す(送れる量が無い欄は飛ばして外側を探す)。

    ウィンドウの境目では止める。開いた一覧(ポップアップ)が短くて送れないとき、その下の画面を動かさないため。
    """
    w = widget
    while w is not None:
        if isinstance(w, QAbstractScrollArea) and w.verticalScrollBar().maximum() > 0:
            return w
        if w.isWindow():
            return None
        w = w.parentWidget()
    return None


def _unit(area: QAbstractScrollArea) -> float:
    """スクロールバーの目盛り 1 つが何 px か(一覧が 1 行ずつ送る設定なら行の高さ)。"""
    if isinstance(area, QAbstractItemView) and \
            area.verticalScrollMode() == QAbstractItemView.ScrollMode.ScrollPerItem:
        h = area.sizeHintForRow(0)
        return float(h if h > 0 else area.fontMetrics().height())
    return 1.0


class AutoScroller(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._area: QAbstractScrollArea | None = None
        self._origin = QPoint()
        self._acc = Accumulator()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    @property
    def active(self) -> bool:
        return self._area is not None

    def eventFilter(self, obj, e) -> bool:
        t = e.type()
        if t == QEvent.Type.MouseButtonPress and isinstance(obj, QWidget):
            if e.button() == Qt.MouseButton.MiddleButton:
                area = find_area(obj)
                if area is not None:
                    self.start(area, e.globalPosition().toPoint())
                    return True
            elif self.active:
                self.stop()     # 他のボタンを押したら止めて、そのクリックは普通に通す
        elif self.active and t == QEvent.Type.MouseButtonRelease and e.button() == Qt.MouseButton.MiddleButton:
            self.stop()
            return True
        elif self.active and t == QEvent.Type.MouseButtonDblClick and e.button() == Qt.MouseButton.MiddleButton:
            return True
        return False

    def start(self, area: QAbstractScrollArea, origin: QPoint) -> None:
        self.stop()
        self._area = area
        self._origin = origin
        self._acc = Accumulator()
        area.destroyed.connect(self.stop)
        QApplication.setOverrideCursor(Qt.CursorShape.SizeVerCursor)
        self._timer.start()

    def stop(self) -> None:
        if self._area is None:
            return
        try:
            self._area.destroyed.disconnect(self.stop)
        except (RuntimeError, TypeError):
            pass
        self._area = None
        self._timer.stop()
        QApplication.restoreOverrideCursor()

    def _tick(self) -> None:
        # 離した瞬間を取りこぼしても(ウィンドウの外で離した等)、押されていなければ止める
        if self._area is None or not (QGuiApplication.mouseButtons() & Qt.MouseButton.MiddleButton):
            self.stop()
            return
        self.scroll_by(step(QCursor.pos().y() - self._origin.y()))

    def scroll_by(self, amount: float) -> None:
        """amount(px)だけ送る。テストからも呼ぶ。"""
        if self._area is None:
            return
        n = self._acc.take(amount, _unit(self._area))
        if n:
            bar = self._area.verticalScrollBar()
            bar.setValue(bar.value() + n)


def install(app: QApplication) -> AutoScroller:
    scroller = AutoScroller(app)
    app.installEventFilter(scroller)
    return scroller
