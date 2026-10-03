"""翻訳の抜け・置換欄の食い違いを検出する。"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

from kn_weapontoolkit import i18n
from kn_weapontoolkit.i18n import en

PKG = Path(__file__).resolve().parent.parent / 'kn_weapontoolkit'
_FIELD_RE = re.compile(r'\{(\w+)\}')


def source_strings() -> dict[str, str]:
    """tr('…') / N_('…') の第1引数(文字列リテラル)を集める。{原文: 最初に出てきた場所}"""
    out: dict[str, str] = {}
    for path in sorted(PKG.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ''
            # checks.py の add(level, '…') も tr() へ渡る
            arg = node.args[1] if name == 'add' and len(node.args) > 1 else node.args[0]
            if name not in ('tr', 'N_', 'add'):
                continue
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if name == 'add' and path.name != 'checks.py':
                    continue
                out.setdefault(arg.value, f'{path.name}:{node.lineno}')
    return out


class I18nTest(unittest.TestCase):
    def test_every_string_is_translated(self):
        missing = {s: where for s, where in source_strings().items() if s not in en.T}
        self.assertEqual(missing, {})

    def test_no_stale_translations(self):
        stale = sorted(set(en.T) - set(source_strings()))
        self.assertEqual(stale, [])

    def test_placeholders_match(self):
        for src, dst in en.T.items():
            self.assertEqual(sorted(_FIELD_RE.findall(src)), sorted(_FIELD_RE.findall(dst)), src)

    def test_normalize(self):
        self.assertEqual(i18n.normalize('ja_JP'), 'ja')
        self.assertEqual(i18n.normalize('ja-JP'), 'ja')
        self.assertEqual(i18n.normalize('en-GB'), 'en')
        self.assertEqual(i18n.normalize('fr_FR'), 'en')     # 未対応の言語は英語
        self.assertEqual(i18n.normalize(''), 'en')
        self.assertEqual(i18n.normalize(None), 'en')

    def test_set_language(self):
        try:
            self.assertEqual(i18n.set_language('en'), 'en')
            self.assertEqual(i18n.tr('武器'), 'Weapon')
            self.assertEqual(i18n.set_language('ja'), 'ja')
            self.assertEqual(i18n.tr('武器'), '武器')
            self.assertIn(i18n.set_language(''), ('ja', 'en'))      # OS の言語
            self.assertEqual(i18n.tr('存在しない原文 {x}', x=1), '存在しない原文 1')
        finally:
            i18n.set_language('ja')


if __name__ == '__main__':
    unittest.main()
