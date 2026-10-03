"""書き出し結果の監査。テンプレートと出力を要素単位で突き合わせ、意図した箇所以外が変わっていないことを確かめる。"""
from __future__ import annotations

import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from kn_weapontoolkit import assets, checks, exporter, i18n
from kn_weapontoolkit.model import ComponentSpec, Project
from kn_weapontoolkit.templates import TemplateLibrary, find_weapon_item
from kn_weapontoolkit.xmlio import MetaError, elements, parse_bytes, parse_file

ROOT = Path(__file__).resolve().parent.parent
LIB = TemplateLibrary(ROOT / 'templates')
NEW_ID = 'WEAPON_AUDIT'


def flatten(root: ET.Element) -> list[tuple[str, tuple, str]]:
    """(パス, 属性, 文字列) の並び。空白の違いとコメントは無視する。"""
    out = []

    def walk(el: ET.Element, path: str) -> None:
        here = f'{path}/{el.tag}'
        text = (el.text or '').strip() if not elements(el) else ''
        out.append((here, tuple(sorted(el.attrib.items())), text))
        for c in elements(el):
            walk(c, here)

    walk(root, '')
    return out


def diff(before: ET.Element, after: ET.Element) -> list[tuple]:
    a, b = flatten(before), flatten(after)
    if len(a) != len(b):
        return [('LENGTH', len(a), len(b))]
    return [(x, y) for x, y in zip(a, b) if x != y]


def project(template: str, **kw) -> Project:
    return Project(template=template, weapon_id=NEW_ID, display_name='Audit', model='w_ar_audit', **kw)


class WeaponAuditTest(unittest.TestCase):
    def test_weapons_meta_changes_only_intended_nodes(self):
        for name in LIB.weapon_names():
            with self.subTest(template=name):
                tpl = LIB.weapon(name)
                before = tpl.weapons_root()
                after = parse_bytes(exporter.build(project(name, slot_order=555), LIB, []).files['meta/weapons.meta'])
                for old, new in diff(before, after):
                    tag = new[0].rsplit('/', 1)[1]
                    if tag in ('Name', 'Model', 'Slot', 'HumanNameHash'):
                        # 武器の定義そのものの直下だけ(末尾の <Name>AR</Name> や弾薬定義の Name は変えない)
                        self.assertEqual(old[2].upper() if tag == 'Name' else None,
                                         tpl.internal_name.upper() if tag == 'Name' else None, new)
                        self.assertIn(new[2], (NEW_ID, 'w_ar_audit', f'SLOT_{NEW_ID}'), new)
                    elif tag == 'Entry':
                        self.assertEqual((old[2], new[2]), (tpl.slot, f'SLOT_{NEW_ID}'))
                    elif tag == 'OrderNumber':
                        self.assertIn('/SlotNavigateOrder/', new[0])
                        self.assertEqual(dict(new[1])['value'], '555')
                    else:
                        self.fail(f'unexpected change: {old} -> {new}')
                # 武器の定義は1つだけ書き換わり、名前は新しい ID になっている
                self.assertEqual(find_weapon_item(after, NEW_ID).findtext('Name'), NEW_ID)

    def test_animations_change_only_keys(self):
        for name in LIB.weapon_names():
            with self.subTest(template=name):
                before = LIB.weapon(name).animations_root()
                res = exporter.build(project(name), LIB, [])
                after = parse_bytes(res.files['meta/weaponanimations.meta'])
                for old, new in diff(before, after):
                    self.assertTrue(new[0].endswith('/WeaponAnimations/Item'), new)
                    self.assertEqual(dict(new[1]).get('key'), NEW_ID)
                keys = [i.get('key') for i in after.findall('WeaponAnimationsSets/Item/WeaponAnimations/Item')]
                if keys:
                    self.assertIn(NEW_ID, keys)

    def test_personality_changes_only_weapon_lists(self):
        for name in LIB.weapon_names():
            with self.subTest(template=name):
                before = LIB.weapon(name).personality_root()
                after = parse_bytes(exporter.build(project(name), LIB, []).files['meta/pedpersonality.meta'])
                # Weapons の中身を除けば同一
                for r in (before, after):
                    for w in list(r.iter('Weapons')):
                        for c in list(w):
                            w.remove(c)
                self.assertEqual(diff(before, after), [])

    def test_component_changes_only_intended_nodes(self):
        for name in LIB.component_names():
            with self.subTest(component=name):
                before = parse_file(LIB.component(name).dir / 'weaponcomponents.meta').find('Infos/Item')
                spec = ComponentSpec(template=name, name='COMPONENT_AUDIT', model='w_at_audit', clip_size=77,
                                     ammo_info='AMMO_RIFLE_FMJ')
                res = exporter.build(project('WEAPON_CARBINERIFLE', components=[spec]), LIB, [])
                after = parse_bytes(res.files['meta/weaponcomponents.meta']).find('Infos/Item')
                for extra in before.findall('WeaponAttachBone'):
                    before.remove(extra)
                for old, new in diff(before, after):
                    tag = new[0].rsplit('/', 1)[1]
                    self.assertIn(tag, ('Name', 'Model', 'ClipSize', 'AmmoInfo'), (old, new))
                self.assertEqual(after.get('type'), before.get('type'))

    def test_template_cache_is_not_mutated_by_builds(self):
        tpl = LIB.weapon('WEAPON_PISTOL')
        snapshot = [flatten(tpl.weapons_root()), flatten(tpl.animations_root()), flatten(tpl.personality_root())]
        exporter.build(project('WEAPON_PISTOL', fire_rate=2.0, fields={'Damage': '1'},
                               components=[ComponentSpec(template='COMPONENT_PISTOL_CLIP_01', name='C')]), LIB, [])
        self.assertEqual(snapshot, [flatten(tpl.weapons_root()), flatten(tpl.animations_root()),
                                    flatten(tpl.personality_root())])
        item = LIB.component('COMPONENT_PISTOL_CLIP_01').item()
        self.assertEqual(item.findtext('Name'), 'COMPONENT_PISTOL_CLIP_01')


class HostileInputTest(unittest.TestCase):
    """壊れた・悪意のあるプロジェクトファイルでも、想定した例外(か点検のエラー)で止まること。"""

    def setUp(self):
        i18n.set_language('ja')

    def test_field_tags_are_not_path_expressions(self):
        p = project('WEAPON_PISTOL', fields={'Explosion/Default/X': 'X', '[': '1', '*': '2', '..': '3', './/Name': 'Z',
                                             'Damage[1]': '9', '': '0', 'Explosion': 'E', '/Damage': '1', 'Fx/': '1'})
        res = exporter.build(p, LIB, [])
        self.assertEqual(sorted(res.skipped_fields), sorted(p.fields))
        item = find_weapon_item(parse_bytes(res.files['meta/weapons.meta']), NEW_ID)
        self.assertEqual(item.findtext('Explosion/Default'), 'DONTCARE')
        self.assertEqual(item.findtext('Name'), NEW_ID)

    def test_template_names_cannot_leave_templates_folder(self):
        for bad in ('../weapons/WEAPON_PISTOL', '..', 'a/b', 'a\\b', '', 'C:\\x', '/etc'):
            with self.assertRaises(MetaError, msg=bad):
                LIB.weapon(bad)
            with self.assertRaises(MetaError, msg=bad):
                LIB.component(bad)

    def test_hostile_project_is_reported_by_checks(self):
        p = Project.from_dict({
            'template': '../../x', 'weapon_id': "W'); os.exit() --", 'display_name': 'a\nb', 'model': '..\\..\\evil',
            'resource_name': '..\\..\\out', 'lod': -5, 'fire_rate': float('nan'), 'fields': {'[': 'x'},
            'components': [{'template': '../x', 'name': '<&>', 'model': 'a/b', 'lod': 0, 'clip_size': -1}],
            'excluded_assets': [1, None],
        })
        issues = checks.run(p, LIB, assets.scan(''))
        self.assertTrue(checks.has_errors(issues))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((exporter.ExportError, MetaError)):
                exporter.export(p, LIB, [], d)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_non_finite_numbers(self):
        for bad in (math.nan, math.inf, 0.0, -1.0):
            p = project('WEAPON_PISTOL', fire_rate=bad)
            self.assertTrue(checks.has_errors(checks.run(p, LIB, assets.scan(''))), bad)
            with self.assertRaises(exporter.ExportError):
                exporter.build(p, LIB, [])
        for bad in ('nan', 'inf', '-inf', '1e999', 'abc', ''):
            p = project('WEAPON_PISTOL', fields={'Damage': bad})
            msgs = [i.message for i in checks.run(p, LIB, assets.scan('')) if i.level == checks.ERROR]
            self.assertTrue(any('Damage' in m for m in msgs), bad)

    def test_special_characters_survive_as_text(self):
        p = project('WEAPON_PISTOL', components=[ComponentSpec(template='COMPONENT_PISTOL_CLIP_01', name='A<&>"B')])
        p.display_name = "x'); print('y"
        res = exporter.build(p, LIB, [])
        comp = parse_bytes(res.files['meta/weaponcomponents.meta']).find('Infos/Item')
        self.assertEqual(comp.findtext('Name'), 'A<&>"B')       # XML として壊れず、文字として入る
        lua = res.files['cl_weaponNames.lua'].decode()
        self.assertEqual(lua, "AddTextEntry('WEAPON_AUDIT', 'x\\'); print(\\'y')\n")

    def test_stale_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for n in ('.weapon_x.abc.tmp', '.weapon_x.def.old', '.weapon_xy.abc.tmp', 'weapon_x', '.weapon_x.txt'):
                (base / n).mkdir()
            self.assertEqual([p.name for p in exporter.stale_dirs(base, 'weapon_x')],
                             ['.weapon_x.abc.tmp', '.weapon_x.def.old'])
            self.assertEqual(exporter.stale_dirs(base / 'missing', 'weapon_x'), [])


if __name__ == '__main__':
    unittest.main()
