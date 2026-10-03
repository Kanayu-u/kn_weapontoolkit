"""画面のテスト(PySide6 がある環境だけ。WSL の stdlib だけの環境では飛ばす)。

    .venv\\Scripts\\python -X utf8 -m unittest tests.test_gui
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

try:
    import PySide6  # noqa: F401
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, 'PySide6 が無い')
class GuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ['KN_WTK_DATA'] = cls.tmp.name      # 利用者の設定に触らない
        Path(cls.tmp.name, 'settings.json').write_text('{"language": "ja"}', encoding='utf-8')
        from kn_weapontoolkit.ui.app import create
        cls.app, cls.win = create(['test'])
        cls.win.show()

    @classmethod
    def tearDownClass(cls):
        cls.win.state.dirty = False
        cls.win.close()
        cls.tmp.cleanup()

    def pump(self):
        for _ in range(5):
            self.app.processEvents()

    def test_find_area_and_scroll(self):
        from kn_weapontoolkit.ui import autoscroll
        combo = self.win.weapon_page.template
        combo.showPopup()
        self.pump()
        view = combo.view()
        self.assertIs(autoscroll.find_area(view.viewport()), view)
        self.assertIsNone(autoscroll.find_area(None))
        scroller = self.app._kn_autoscroll
        bar = view.verticalScrollBar()
        bar.setValue(0)
        scroller.start(view, view.mapToGlobal(view.rect().center()))
        try:
            for _ in range(20):
                scroller.scroll_by(30.0)
            self.assertGreater(bar.value(), 0)
            moved = bar.value()
            for _ in range(20):
                scroller.scroll_by(-30.0)
            self.assertLess(bar.value(), moved)
        finally:
            scroller.stop()
        self.assertFalse(scroller.active)
        combo.hidePopup()

    def test_short_popup_does_not_scroll_page_below(self):
        # 送れない短い一覧(ポップアップ)の上で押しても、その下の画面(スクロールできる欄)を動かさない
        from PySide6.QtWidgets import QComboBox, QScrollArea, QVBoxLayout, QWidget
        from kn_weapontoolkit.ui import autoscroll
        area = QScrollArea()
        inner = QWidget()
        inner.setMinimumHeight(3000)
        combo = QComboBox(inner)
        combo.addItems(['a', 'b'])
        QVBoxLayout(inner).addWidget(combo)
        area.setWidget(inner)
        area.resize(200, 200)
        area.show()
        combo.showPopup()
        self.pump()
        try:
            self.assertGreater(area.verticalScrollBar().maximum(), 0)
            self.assertIsNone(autoscroll.find_area(combo.view().viewport()))
            self.assertIs(autoscroll.find_area(combo), area)       # 閉じた一覧の上なら画面を送る
        finally:
            combo.hidePopup()
            area.close()

    def test_middle_click_keeps_popup_open(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        combo = self.win.weapon_page.template
        QTest.qWait(400)    # 閉じた直後の再表示は Qt が無視するため、前のテストの後に少し待つ
        combo.showPopup()
        self.pump()
        view = combo.view()
        scroller = self.app._kn_autoscroll
        self.assertTrue(view.isVisible(), '一覧が開いていない')
        pos = view.viewport().rect().center()
        QTest.mousePress(view.viewport(), Qt.MouseButton.MiddleButton, pos=pos)
        self.assertTrue(scroller.active)
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.MiddleButton, pos=pos)
        self.pump()
        self.assertFalse(scroller.active)
        self.assertTrue(view.isVisible(), 'ホイールのボタンで一覧が閉じた')
        combo.hidePopup()

    def test_middle_click_on_unscrollable_passes_through(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.mousePress(self.win.reset_btn, Qt.MouseButton.MiddleButton)
        self.assertFalse(self.app._kn_autoscroll.active)
        QTest.mouseRelease(self.win.reset_btn, Qt.MouseButton.MiddleButton)

    def test_reset(self):
        from kn_weapontoolkit.model import ComponentSpec, Project
        w = self.win
        p = w.state.project
        p.template = 'WEAPON_PISTOL'
        p.weapon_id = 'WEAPON_TESTRESET'
        p.display_name = 'Reset Me'
        p.fields['Damage'] = '99'
        p.fire_rate = 0.5
        p.components.append(ComponentSpec(template='COMPONENT_AT_PI_SUPP', name='COMPONENT_X', model='w_x'))
        w.state.touch()
        w.show_page(2)
        w._confirm_discard = lambda: True            # 保存の確認は出さずに進める
        try:
            w.reset_btn.click()
        finally:
            del w._confirm_discard
        self.pump()
        fresh = Project()
        q = w.state.project
        self.assertIsNot(q, p)
        self.assertEqual((q.template, q.weapon_id, q.display_name, q.fields, q.components, q.fire_rate),
                         (fresh.template, fresh.weapon_id, fresh.display_name, {}, [], None))
        self.assertFalse(w.state.dirty)
        self.assertEqual(w.stack.currentIndex(), 0)
        self.assertEqual(w.weapon_page.weapon_id.text(), fresh.weapon_id)

    def test_reset_cancel_keeps_project(self):
        w = self.win
        p = w.state.project
        p.weapon_id = 'WEAPON_KEEPME'
        w.state.touch()
        w._confirm_discard = lambda: False
        try:
            w.reset_btn.click()
        finally:
            del w._confirm_discard
        self.assertIs(w.state.project, p)
        self.assertEqual(w.state.project.weapon_id, 'WEAPON_KEEPME')


if __name__ == '__main__':
    unittest.main()
