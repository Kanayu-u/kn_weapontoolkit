"""3パスレビュー(2026-10-03)で直した点の回帰テスト。GUI は使わない。"""
from __future__ import annotations

import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

from kn_weapontoolkit import assets, checks, exporter, i18n, importer
from kn_weapontoolkit.model import ComponentSpec, Project
from kn_weapontoolkit.templates import TemplateLibrary, find_weapon_item
from kn_weapontoolkit.xmlio import parse_bytes

ROOT = Path(__file__).resolve().parent.parent
LIB = TemplateLibrary(ROOT / 'templates')


def errors_and_warnings(p: Project) -> list[str]:
    i18n.set_language('ja')
    return [i.message for i in checks.run(p, LIB, assets.scan('')) if i.level in (checks.ERROR, checks.WARNING)]


class ReviewTest(unittest.TestCase):
    def test_scan_stops_on_huge_folder_without_models(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(30):
                (Path(d) / f'note{i}.txt').write_text('x')
            (Path(d) / 'sub').mkdir()
            (Path(d) / 'sub' / 'w_x.ydr').write_bytes(b'RSC7')
            self.assertEqual([a.name for a in assets.scan(d).assets], ['w_x.ydr'])
            with mock.patch.object(assets, 'MAX_VISITED', 10):
                r = assets.scan(d)
            self.assertTrue(r.truncated)

    def test_clip_size_inf_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / 'components' / 'COMPONENT_TEST_CLIP'
            c.mkdir(parents=True)
            (c / 'weaponcomponents.meta').write_text(
                '<CWeaponComponentInfoBlob><Infos><Item type="CWeaponComponentClipInfo"><Name>COMPONENT_TEST_CLIP</Name>'
                '<ClipSize value="inf" /></Item></Infos></CWeaponComponentInfoBlob>', encoding='utf-8')
            self.assertEqual(TemplateLibrary(Path(d)).component('COMPONENT_TEST_CLIP').clip_size, 0)

    def test_fields_cannot_overwrite_managed_tags(self):
        # 手で書き換えたプロジェクトの fields に Name / Model があっても、専用の欄の値を使う
        p = Project(template='WEAPON_CARBINERIFLE', weapon_id='WEAPON_REAL', model='w_real',
                    fields={'Name': 'WEAPON_FAKE', 'Model': 'w_fake', 'Damage': '50'})
        res = exporter.build(p, LIB, [])
        item = find_weapon_item(parse_bytes(res.files['meta/weapons.meta']), 'WEAPON_REAL')
        self.assertEqual(item.find('Name').text, 'WEAPON_REAL')
        self.assertEqual(item.find('Model').text, 'w_real')
        self.assertEqual(item.find('Damage').get('value'), '50')
        self.assertEqual(sorted(res.skipped_fields), ['Model', 'Name'])

    def test_number_with_underscore_is_rejected(self):
        msgs = errors_and_warnings(Project(template='WEAPON_CARBINERIFLE', weapon_id='WEAPON_X', model='w_x',
                                           fields={'Damage': '1_000'}))
        self.assertTrue(any('数値ではありません' in m for m in msgs))

    def test_slot_order_and_bone_name(self):
        p = Project(template='WEAPON_CARBINERIFLE', weapon_id='WEAPON_X', model='w_x', slot_order=0,
                    components=[ComponentSpec(template='COMPONENT_AT_AR_SUPP', name='COMPONENT_X_SUPP',
                                              model='w_at_ar_supp', bone='WAP Supp<')])
        msgs = errors_and_warnings(p)
        self.assertTrue(any('並び順は 1 以上' in m for m in msgs))
        self.assertTrue(any('ボーン名に使えない文字' in m for m in msgs))
        p.slot_order, p.components[0].bone = 5, 'WAPSupp_3'     # 自作モデルの独自ボーンは通す
        msgs = errors_and_warnings(p)
        self.assertFalse([m for m in msgs if '並び順は 1 以上' in m or 'ボーン名に使えない文字' in m])

    def test_work_folders_are_not_listed_as_templates(self):
        with tempfile.TemporaryDirectory() as d:
            src = ROOT / 'templates' / 'weapons' / 'WEAPON_PISTOL'
            shutil.copytree(src, Path(d) / 'weapons' / 'WEAPON_PISTOL')
            shutil.copytree(src, Path(d) / 'weapons' / '.WEAPON_PISTOL.abc.old')
            self.assertEqual(TemplateLibrary(Path(d)).weapon_names(), ['WEAPON_PISTOL'])

    def test_write_template_keeps_old_when_replace_fails(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / 'weapons' / 'WEAPON_T'
            importer.write_template(folder, {'weapons.meta': ET.Element('Old')})
            real_rename = importer.os.rename
            calls = []

            def flaky(a, b):
                calls.append((Path(a).name, Path(b).name))
                if str(a).endswith('.tmp'):
                    raise OSError('locked')
                return real_rename(a, b)
            with mock.patch.object(importer.os, 'rename', flaky):
                with self.assertRaises(OSError):
                    importer.write_template(folder, {'weapons.meta': ET.Element('New')})
            self.assertIn(b'<Old', (folder / 'weapons.meta').read_bytes())     # 前のテンプレートが残っている
            self.assertEqual([p.name for p in folder.parent.iterdir()], ['WEAPON_T'])  # 作業フォルダは残さない
            importer.write_template(folder, {'weapons.meta': ET.Element('New')})
            self.assertIn(b'<New', (folder / 'weapons.meta').read_bytes())
            self.assertEqual([p.name for p in folder.parent.iterdir()], ['WEAPON_T'])

    def test_import_rejects_path_like_names(self):
        with tempfile.TemporaryDirectory() as d:
            failed = importer.import_into(importer.MetaIndex(), Path(d), TemplateLibrary(Path(d)),
                                          ['../evil'], ['..\\x'])
            self.assertEqual(sorted(n for n, _ in failed), ['../evil', '..\\x'])
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_meta_scan_stops_on_huge_folder(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(5):
                (Path(d) / f'{i}.meta').write_text('<CWeaponInfoBlob />', encoding='utf-8')
            with mock.patch.object(importer, 'MAX_META_FILES', 2):
                idx = importer.MetaIndex.scan([d])
            self.assertTrue(idx.truncated)
            self.assertEqual(idx.files, 2)
            self.assertFalse(importer.MetaIndex.scan([d]).truncated)


if __name__ == '__main__':
    unittest.main()
