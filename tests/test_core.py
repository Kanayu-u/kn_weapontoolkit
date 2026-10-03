"""コア(テンプレート読込・meta 生成・書き出し・点検)のテスト。GUI は使わない。"""
from __future__ import annotations

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from kn_weapontoolkit import assets, checks, exporter, i18n
from kn_weapontoolkit.model import ComponentSpec, Project, ProjectError, sanitize_resource_name
from kn_weapontoolkit.templates import TemplateLibrary, find_weapon_item
from kn_weapontoolkit.xmlio import MetaError, parse_bytes

ROOT = Path(__file__).resolve().parent.parent
LIB = TemplateLibrary(ROOT / 'templates')


def make_assets(folder: Path, names: list[str]) -> list[assets.Asset]:
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        p = folder / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'RSC7' + n.encode())
    return assets.scan(folder).assets


def project(template: str = 'WEAPON_CARBINERIFLE', **kw) -> Project:
    kw.setdefault('model', 'w_ar_testgun')
    return Project(template=template, weapon_id='WEAPON_TESTGUN', display_name='Test Gun', **kw)


def comp(template: str, name: str = '', **kw) -> ComponentSpec:
    return ComponentSpec(template=template, name=name or template.replace('COMPONENT_', 'COMPONENT_TG_'), **kw)


def meta(res: exporter.BuildResult, name: str) -> ET.Element:
    return parse_bytes(res.files[f'meta/{name}'], name)


def weapon_item(res: exporter.BuildResult) -> ET.Element:
    return find_weapon_item(meta(res, 'weapons.meta'), 'WEAPON_TESTGUN')


def attach_points(res: exporter.BuildResult) -> list[tuple[str, list[tuple[str, str]]]]:
    out = []
    for p in weapon_item(res).findall('AttachPoints/Item'):
        comps = [(c.findtext('Name'), c.find('Default').get('value')) for c in p.findall('Components/Item')]
        out.append((p.findtext('AttachBone'), comps))
    return out


class TemplatesTest(unittest.TestCase):
    def test_all_templates_load(self):
        self.assertEqual(LIB.scan_problems(), [])
        self.assertGreaterEqual(len(LIB.weapon_names()), 60)
        self.assertGreaterEqual(len(LIB.component_names()), 90)

    def test_every_component_has_a_weapon_bone(self):
        # 元ツールは WeaponAttachBone の無いテンプレートで落ちていた。補完で全部決まること
        for n in LIB.component_names():
            self.assertTrue(LIB.component(n).weapon_bone, n)

    def test_bone_inference(self):
        self.assertEqual(LIB.component('COMPONENT_BULLPUPRIFLE_CLIP_01').weapon_bone, 'WAPClip')
        self.assertEqual(LIB.component('COMPONENT_RPG_CLIP_01').weapon_bone, 'WAPClip')
        self.assertEqual(LIB.component('COMPONENT_AT_MUZZLE_01').weapon_bone, 'WAPSupp')
        self.assertEqual(LIB.component('COMPONENT_AT_AR_BARREL_01').weapon_bone, 'WAPBarrel')
        # 明示されているものはそれを優先する
        self.assertEqual(LIB.component('COMPONENT_AT_SCOPE_LARGE_FIXED_ZOOM').weapon_bone, 'WAPScop_2')

    def test_weapon_item_found_by_type(self):
        # 弾薬定義が先に並ぶテンプレートでも武器の定義を拾う
        t = LIB.weapon('WEAPON_RAILGUNXM3')
        self.assertEqual(t.internal_name, 'WEAPON_RAILGUNXM3')

    def test_missing_template(self):
        with self.assertRaises(MetaError):
            LIB.weapon('WEAPON_DOES_NOT_EXIST')


class BuildTest(unittest.TestCase):
    def check_weapon_build(self, template: str, res: exporter.BuildResult):
        item = weapon_item(res)
        self.assertIsNotNone(item, template)
        self.assertEqual(item.findtext('Name'), 'WEAPON_TESTGUN')
        self.assertEqual(item.findtext('Model'), 'w_ar_testgun')
        self.assertEqual(item.findtext('Slot'), 'SLOT_WEAPON_TESTGUN')
        self.assertEqual(item.findtext('HumanNameHash'), 'WEAPON_TESTGUN')
        old_slot = LIB.weapon(template).slot
        root = meta(res, 'weapons.meta')
        for sec in ('SlotNavigateOrder', 'SlotBestOrder'):
            for e in root.findall(f'{sec}//Entry'):
                self.assertNotEqual(e.text, old_slot, f'{template} {sec}')
        if 'meta/weaponanimations.meta' in res.files:
            anim = meta(res, 'weaponanimations.meta')
            keys = [i.get('key') for i in anim.findall('WeaponAnimationsSets/Item/WeaponAnimations/Item')]
            self.assertNotIn(LIB.weapon(template).internal_name, keys, template)
        if 'meta/pedpersonality.meta' in res.files:
            pp = meta(res, 'pedpersonality.meta')
            for w in pp.iter('Weapons'):
                self.assertEqual([i.text for i in w.findall('Item')], ['WEAPON_TESTGUN'], template)
        for name, data in res.files.items():
            if name.endswith('.meta'):
                self.assertTrue(data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>\r\n'), name)
                self.assertNotIn(b'UTF - 8', data)
                parse_bytes(data, name)

    def test_every_weapon_template_builds(self):
        for t in LIB.weapon_names():
            with self.subTest(template=t):
                res = exporter.build(project(t, slot_order=432), LIB, [])
                self.check_weapon_build(t, res)
                manifest = res.files['fxmanifest.lua'].decode()
                self.assertIn("data_file 'WEAPONINFO_FILE' 'meta/weapons.meta'", manifest)
                self.assertNotIn('weaponcomponents.meta', manifest)     # 部品なしなら載せない

    def test_every_component_template_builds(self):
        # 元ツールで落ちていた組み合わせ(ブルパップ/RPG のクリップ等)を含め、全部品を1つずつ付けて書き出す
        for w in ('WEAPON_BULLPUPRIFLE', 'WEAPON_RPG', 'WEAPON_CARBINERIFLE'):
            for c in LIB.component_names():
                with self.subTest(weapon=w, component=c):
                    p = project(w, components=[comp(c, 'COMPONENT_TG_X', model='w_ar_testgun_x', default=True)])
                    res = exporter.build(p, LIB, [])
                    self.check_weapon_build(w, res)
                    bone = exporter.component_bone(p.components[0], LIB.component(c), LIB.weapon(w))
                    self.assertTrue(bone)
                    self.assertIn((bone, [('COMPONENT_TG_X', 'true')]), attach_points(res))
                    item = meta(res, 'weaponcomponents.meta').find('Infos/Item')
                    self.assertEqual(item.findtext('Name'), 'COMPONENT_TG_X')
                    self.assertIsNone(item.find('WeaponAttachBone'))

    def test_all_components_at_once(self):
        comps = [comp(c, f'COMPONENT_TG_{i}') for i, c in enumerate(LIB.component_names())]
        res = exporter.build(project(components=comps), LIB, [])
        items = meta(res, 'weaponcomponents.meta').findall('Infos/Item')
        self.assertEqual(len(items), len(comps))
        bones = [b for b, _ in attach_points(res)]
        self.assertEqual(len(bones), len(set(bones)), '同じボーンの AttachPoint が複数ある')
        self.assertEqual(sum(len(c) for _, c in attach_points(res)), len(comps))

    def test_bullpup_and_rpg_regression(self):
        p = project('WEAPON_BULLPUPRIFLE', components=[
            comp('COMPONENT_BULLPUPRIFLE_CLIP_01', 'COMPONENT_TG_CLIP_01', model='w_ar_testgun_mag1', clip_size=25,
                 default=True),
            comp('COMPONENT_BULLPUPRIFLE_CLIP_02', 'COMPONENT_TG_CLIP_02', model='w_ar_testgun_mag2', clip_size=50),
        ])
        res = exporter.build(p, LIB, [])
        for name in ('weapons.meta', 'weaponarchetypes.meta', 'weaponanimations.meta', 'pedpersonality.meta',
                     'weaponcomponents.meta'):
            self.assertIn(f'meta/{name}', res.files)
        self.assertEqual(attach_points(res),
                         [('WAPClip', [('COMPONENT_TG_CLIP_01', 'true'), ('COMPONENT_TG_CLIP_02', 'false')])])
        clips = meta(res, 'weaponcomponents.meta').findall('Infos/Item')
        self.assertEqual([c.find('ClipSize').get('value') for c in clips], ['25', '50'])
        self.assertEqual([c.findtext('Model') for c in clips], ['w_ar_testgun_mag1', 'w_ar_testgun_mag2'])

        p = project('WEAPON_RPG', components=[comp('COMPONENT_RPG_CLIP_01', 'COMPONENT_TG_CLIP_01', default=True)])
        res = exporter.build(p, LIB, [])
        self.assertEqual(attach_points(res), [('WAPClip', [('COMPONENT_TG_CLIP_01', 'true')])])
        self.assertEqual(len(res.files), 7)

    def test_template_attachments_replaced_per_bone(self):
        # ADVANCEDRIFLE のテンプレートは WAPClip / WAPFlshLasr / WAPScop / WAPSupp を持つ
        p = project('WEAPON_ADVANCEDRIFLE', components=[comp('COMPONENT_ADVANCEDRIFLE_CLIP_01', 'COMPONENT_TG_CLIP')])
        ap = dict(attach_points(exporter.build(p, LIB, [])))
        self.assertEqual(ap['WAPClip'], [('COMPONENT_TG_CLIP', 'false')])
        self.assertEqual([n for n, _ in ap['WAPSupp']], ['COMPONENT_AT_AR_SUPP'])
        p.keep_template_attachments = False
        self.assertEqual(attach_points(exporter.build(p, LIB, [])), [('WAPClip', [('COMPONENT_TG_CLIP', 'false')])])

    def test_bone_override(self):
        p = project(components=[comp('COMPONENT_AT_AR_SUPP', 'COMPONENT_TG_SUPP', bone='WAPSupp_2')])
        self.assertEqual(attach_points(exporter.build(p, LIB, [])), [('WAPSupp_2', [('COMPONENT_TG_SUPP', 'false')])])

    def test_field_overrides(self):
        p = project(fields={'Damage': '55.5', 'AmmoInfo': 'AMMO_SMG', 'Audio': 'AUDIO_ITEM_SMG', 'NoSuchField': '1',
                            'Explosion': 'x', 'Explosion/HitCar': 'GRENADE', 'Fx/FlashFx': 'muz_rpg'})
        res = exporter.build(p, LIB, [])
        item = weapon_item(res)
        self.assertEqual(item.find('Damage').get('value'), '55.5')
        self.assertEqual(item.find('AmmoInfo').get('ref'), 'AMMO_SMG')
        self.assertEqual(item.findtext('Audio'), 'AUDIO_ITEM_SMG')
        self.assertIsNone(item.find('NoSuchField'))
        self.assertEqual(sorted(res.skipped_fields), ['Explosion', 'NoSuchField'])   # 入れ物そのものは値ではない
        self.assertEqual(item.findtext('Explosion/Default'), 'DONTCARE')
        self.assertEqual(item.findtext('Explosion/HitCar'), 'GRENADE')                 # 一段下の項目は書ける
        self.assertEqual(item.findtext('Fx/FlashFx'), 'muz_rpg')

    def test_slot_order(self):
        res = exporter.build(project(slot_order=777), LIB, [])
        order = meta(res, 'weapons.meta').find('SlotNavigateOrder/Item/WeaponSlots/Item/OrderNumber')
        self.assertEqual(order.get('value'), '777')
        res = exporter.build(project(), LIB, [])     # 未採番ならテンプレートの値のまま
        order = meta(res, 'weapons.meta').find('SlotNavigateOrder/Item/WeaponSlots/Item/OrderNumber')
        self.assertEqual(order.get('value'), '300')

    def test_fire_rate(self):
        res = exporter.build(project('WEAPON_COMBATSHOTGUN', fire_rate=1.5), LIB, [])
        # AnimFireRateModifier の無いセットを持つテンプレート(元ツールはここで落ちた)
        rates = [i.find('AnimFireRateModifier').get('value')
                 for i in meta(res, 'weaponanimations.meta').findall('WeaponAnimationsSets/Item/WeaponAnimations/Item')]
        self.assertTrue(rates)
        self.assertEqual(set(rates), {'1.500000'})
        src = LIB.weapon('WEAPON_CARBINERIFLE').animations_root()
        before = [i.find('AnimFireRateModifier').get('value')
                  for i in src.findall('WeaponAnimationsSets/Item/WeaponAnimations/Item')]
        res = exporter.build(project(), LIB, [])     # 指定なしならテンプレートの値を変えない
        after = [i.find('AnimFireRateModifier').get('value')
                 for i in meta(res, 'weaponanimations.meta').findall('WeaponAnimationsSets/Item/WeaponAnimations/Item')]
        self.assertEqual(before, after)

    def test_archetypes(self):
        with tempfile.TemporaryDirectory() as d:
            found = make_assets(Path(d), ['W_AR_TestGun.ydr', 'w_ar_testgun_hi.ydr', 'w_ar_testgun.ytd',
                                          'w_ar_testgun+hi.ytd', 'w_ar_testgun_mag1.ydr', 'w_ar_testgun_supp.ydr',
                                          'w_ar_testgun_supp.ytd', 'notes.txt'])
            p = project(lod=450, components=[comp('COMPONENT_CARBINERIFLE_CLIP_01', model='w_ar_testgun_mag1', lod=250)])
            arch = meta(exporter.build(p, LIB, found), 'weaponarchetypes.meta')
            rows = [(i.findtext('modelName'), i.findtext('txdName'), i.find('lodDist').get('value'))
                    for i in arch.findall('InitDatas/Item')]
            self.assertEqual(rows, [('W_AR_TestGun', 'W_AR_TestGun', '450'),
                                    ('w_ar_testgun_mag1', 'w_ar_testgun', '250'),      # 自前の .ytd が無い → 武器本体のを使う
                                    ('w_ar_testgun_supp', 'w_ar_testgun_supp', '450')])
            self.assertEqual({i.findtext('ptfxAssetName') for i in arch.findall('InitDatas/Item')}, {'NULL'})

    def test_names_script_escaping(self):
        p = project()
        p.display_name = "O'Brien \\ \"X\" 日本語"
        self.assertEqual(exporter.build_names_script(p),
                         "AddTextEntry('WEAPON_TESTGUN', 'O\\'Brien \\\\ \"X\" 日本語')\n")


class ExportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # 元ツールは日本語を含むパスでモデルを読めなかった
        self.base = Path(self._tmp.name) / 'デスクトップ 武器' / 'my gun'
        self.src = self.base / 'モデル'
        self.out = self.base / '出力 先'
        self.out.mkdir(parents=True)
        self.assets = make_assets(self.src, ['w_ar_testgun.ydr', 'w_ar_testgun_hi.ydr', 'w_ar_testgun.ytd',
                                             'sub/w_ar_testgun_mag1.ydr'])

    def leftovers(self) -> list[str]:
        return sorted(p.name for p in self.out.iterdir())

    def test_export_with_non_ascii_paths(self):
        self.assertEqual(len(self.assets), 4)
        p = project(import_dir=str(self.src))
        target = exporter.export(p, LIB, self.assets, self.out)
        self.assertEqual(target, self.out / 'weapon_testgun')
        self.assertEqual(self.leftovers(), ['weapon_testgun'])
        self.assertEqual(sorted(f.name for f in (target / 'stream').iterdir()),
                         ['w_ar_testgun.ydr', 'w_ar_testgun.ytd', 'w_ar_testgun_hi.ydr', 'w_ar_testgun_mag1.ydr'])
        self.assertEqual((target / 'stream' / 'w_ar_testgun.ydr').read_bytes(), b'RSC7w_ar_testgun.ydr')
        self.assertEqual(sorted(f.name for f in (target / 'meta').iterdir()),
                         ['pedpersonality.meta', 'weaponanimations.meta', 'weaponarchetypes.meta', 'weapons.meta'])
        self.assertTrue((target / 'fxmanifest.lua').is_file())
        self.assertTrue((target / 'cl_weaponNames.lua').is_file())

    def test_independent_of_working_directory(self):
        cwd = os.getcwd()
        os.chdir(self._tmp.name)
        try:
            exporter.export(project(), TemplateLibrary(ROOT / 'templates'), self.assets, self.out)
        finally:
            os.chdir(cwd)
        self.assertEqual(self.leftovers(), ['weapon_testgun'])

    def test_existing_folder(self):
        p = project()
        exporter.export(p, LIB, self.assets, self.out)
        with self.assertRaises(FileExistsError):
            exporter.export(p, LIB, self.assets, self.out)
        p.display_name = 'Second'
        exporter.export(p, LIB, self.assets, self.out, overwrite=True)
        self.assertIn('Second', (self.out / 'weapon_testgun' / 'cl_weaponNames.lua').read_text(encoding='utf-8'))
        self.assertEqual(self.leftovers(), ['weapon_testgun'])

    def test_refuses_to_replace_non_resource_folder(self):
        other = self.out / 'weapon_testgun'
        other.mkdir()
        (other / 'important.txt').write_text('keep me')
        with self.assertRaises(exporter.ExportError):
            exporter.export(project(), LIB, self.assets, self.out, overwrite=True)
        self.assertEqual((other / 'important.txt').read_text(), 'keep me')
        self.assertEqual(self.leftovers(), ['weapon_testgun'])

    def test_failure_leaves_nothing_behind(self):
        (self.src / 'w_ar_testgun.ytd').unlink()      # 走査後にファイルが消えた
        with self.assertRaises(exporter.ExportError):
            exporter.export(project(), LIB, self.assets, self.out)
        self.assertEqual(self.leftovers(), [])

    def test_failed_overwrite_keeps_previous_export(self):
        p = project()
        exporter.export(p, LIB, self.assets, self.out)
        (self.src / 'w_ar_testgun.ytd').unlink()
        with self.assertRaises(exporter.ExportError):
            exporter.export(p, LIB, self.assets, self.out, overwrite=True)
        self.assertEqual(self.leftovers(), ['weapon_testgun'])
        self.assertTrue((self.out / 'weapon_testgun' / 'stream' / 'w_ar_testgun.ytd').is_file())

    def test_excluded_assets(self):
        p = project(excluded_assets=['w_ar_testgun_mag1.ydr'])
        target = exporter.export(p, LIB, self.assets, self.out)
        self.assertNotIn('w_ar_testgun_mag1.ydr', [f.name for f in (target / 'stream').iterdir()])
        self.assertNotIn(b'mag1', (target / 'meta' / 'weaponarchetypes.meta').read_bytes())

    def test_resource_name_cannot_escape_output_folder(self):
        for bad in ('..', '../evil', 'a/b', 'a\\b', 'C:evil', ''):
            p = project(resource_name=bad)
            if not bad:
                p.weapon_id = ''
            with self.assertRaises(exporter.ExportError, msg=bad):
                exporter.export(p, LIB, self.assets, self.out)
        self.assertEqual(self.leftovers(), [])
        self.assertEqual(sorted(x.name for x in self.base.iterdir()), ['モデル', '出力 先'])

    def test_missing_output_folder(self):
        with self.assertRaises(exporter.ExportError):
            exporter.export(project(), LIB, self.assets, self.out / 'nope')


class AssetsTest(unittest.TestCase):
    def test_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / '武器 フォルダ'
            make_assets(root, ['W_PI_Gun.YDR', 'w_pi_gun_hi.ydr', 'w_pi_gun+hi.ytd', 'a/w_pi_gun.ydr', 'readme.md',
                               'clip@anim.ycd'])
            r = assets.scan(root)
            self.assertEqual([a.name for a in r.assets], ['clip@anim.ycd', 'w_pi_gun+hi.ytd', 'W_PI_Gun.YDR',
                                                          'w_pi_gun_hi.ydr'])
            self.assertEqual(len(r.duplicates), 1)
            by = {a.key: a for a in r.assets}
            self.assertEqual(by['w_pi_gun.ydr'].base, 'w_pi_gun')
            self.assertEqual(by['w_pi_gun_hi.ydr'].base, 'w_pi_gun')
            self.assertEqual(by['w_pi_gun+hi.ytd'].base, 'w_pi_gun')
            self.assertTrue(by['w_pi_gun.ydr'].is_base_model)
            self.assertFalse(by['w_pi_gun_hi.ydr'].is_base_model)

    def test_scan_missing_folder(self):
        self.assertEqual(assets.scan('').assets, [])
        self.assertEqual(assets.scan('/no/such/folder/here').assets, [])


class ProjectTest(unittest.TestCase):
    def test_roundtrip(self):
        p = project(fields={'Damage': '40'}, fire_rate=1.2, slot_order=401, excluded_assets=['a.ydr'],
                    components=[comp('COMPONENT_AT_AR_SUPP', clip_size=None, bone='WAPSupp_2', default=True)])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / '保存 先.kwtk.json'
            p.save(path)
            self.assertEqual(Project.load(path), p)
            self.assertEqual([f.name for f in Path(d).iterdir()], ['保存 先.kwtk.json'])

    def test_tolerates_bad_values(self):
        p = Project.from_dict({'weapon_id': 'WEAPON_X', 'lod': 'abc', 'fire_rate': None, 'fields': 'oops', 'extra': 1,
                               'components': [{'template': 'T', 'clip_size': '12', 'default': 'yes'}, 5],
                               'excluded_assets': ['A.YDR']})
        self.assertEqual(p.weapon_id, 'WEAPON_X')
        self.assertEqual(p.lod, 500)
        self.assertEqual(p.fields, {})
        self.assertEqual(len(p.components), 1)
        self.assertIsNone(p.components[0].clip_size)
        self.assertFalse(p.components[0].default)
        self.assertEqual(p.excluded_assets, ['a.ydr'])

    def test_load_errors(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / 'bad.json'
            bad.write_text('{not json', encoding='utf-8')
            with self.assertRaises(ProjectError):
                Project.load(bad)
            with self.assertRaises(ProjectError):
                Project.load(Path(d) / 'missing.json')
            (Path(d) / 'list.json').write_text('[1]', encoding='utf-8')
            with self.assertRaises(ProjectError):
                Project.load(Path(d) / 'list.json')

    def test_resource_name(self):
        self.assertEqual(sanitize_resource_name(' WEAPON_AK 47! '), 'weapon_ak_47')
        self.assertEqual(project().effective_resource_name(), 'weapon_testgun')
        self.assertEqual(project(resource_name='my-gun').effective_resource_name(), 'my-gun')


class ChecksTest(unittest.TestCase):
    def run_checks(self, p: Project, names: list[str]) -> list[checks.Issue]:
        i18n.set_language('ja')
        with tempfile.TemporaryDirectory() as d:
            make_assets(Path(d), names)
            p.import_dir = d
            return checks.run(p, LIB, assets.scan(d))

    def levels(self, issues, level):
        return [i.message for i in issues if i.level == level]

    def test_clean_project(self):
        issues = self.run_checks(project(slot_order=400), ['w_ar_testgun.ydr', 'w_ar_testgun_hi.ydr', 'w_ar_testgun.ytd'])
        self.assertEqual(issues, [])

    def test_missing_model(self):
        issues = self.run_checks(project(), ['w_ar_other.ydr'])
        self.assertTrue(checks.has_errors(issues))
        self.assertTrue(any('w_ar_testgun.ydr' in m for m in self.levels(issues, checks.ERROR)))
        self.assertTrue(any('w_ar_other.ydr' in m for m in self.levels(issues, checks.WARNING)))

    def test_no_folder(self):
        i18n.set_language('ja')
        issues = checks.run(project(), LIB, assets.scan(''))
        self.assertTrue(checks.has_errors(issues))

    def test_game_model_without_files(self):
        # バニラ武器のモデル名なら、フォルダが無くても書き出せる(注意は出す)
        i18n.set_language('ja')
        issues = checks.run(project(model='w_ar_carbinerifle'), LIB, assets.scan(''))
        self.assertFalse(checks.has_errors(issues), issues)
        self.assertTrue(any('w_ar_carbinerifle' in m for m in self.levels(issues, checks.WARNING)))
        # 部品のモデルだけが入ったフォルダでも同じ
        p = project(model='w_ar_carbinerifle')
        self.assertFalse(checks.has_errors(self.run_checks(p, ['w_ar_testgun_mag1.ydr'])))
        res = exporter.build(p, LIB, [])
        self.assertEqual(list(meta(res, 'weaponarchetypes.meta').find('InitDatas')), [])
        self.assertFalse(any(k.startswith('stream/') for k in res.files))

    def test_streamed_model_shadows_vanilla(self):
        issues = self.run_checks(project(model='w_ar_carbinerifle'), ['w_ar_carbinerifle.ydr'])
        self.assertFalse(checks.has_errors(issues))
        self.assertTrue(any('置き換わります' in m for m in self.levels(issues, checks.INFO)))
        self.assertFalse(any('同梱しません' in m for m in self.levels(issues, checks.WARNING)))

    def test_ids(self):
        p = project()
        p.weapon_id = 'WEAPON_PISTOL'
        w = self.levels(self.run_checks(p, ['w_ar_testgun.ydr']), checks.WARNING)
        self.assertTrue(any('バニラ武器' in m for m in w))
        p.weapon_id = 'weapon bad'
        self.assertTrue(checks.has_errors(self.run_checks(p, ['w_ar_testgun.ydr'])))

    def test_components(self):
        p = project(components=[
            comp('COMPONENT_CARBINERIFLE_CLIP_01', 'COMPONENT_CARBINERIFLE_CLIP_01', model='w_ar_testgun_mag1',
                 default=True),
            comp('COMPONENT_CARBINERIFLE_CLIP_02', 'COMPONENT_TG_CLIP_02', model='w_ar_missing', default=True),
            comp('COMPONENT_AT_AR_SUPP', 'COMPONENT_TG_CLIP_02'),
        ])
        issues = self.run_checks(p, ['w_ar_testgun.ydr', 'w_ar_testgun_mag1.ydr'])
        errors, warns = self.levels(issues, checks.ERROR), self.levels(issues, checks.WARNING)
        self.assertTrue(any('重複' in m for m in errors))
        self.assertTrue(any('バニラと同じ' in m for m in warns))
        self.assertTrue(any('w_ar_missing.ydr' in m for m in warns))
        self.assertTrue(any('WAPClip' in m and '複数' in m for m in warns))

    def test_bad_field_value(self):
        issues = self.run_checks(project(fields={'Damage': 'abc', 'Bogus': '1'}), ['w_ar_testgun.ydr'])
        self.assertTrue(any('Damage' in m for m in self.levels(issues, checks.ERROR)))
        self.assertTrue(any('Bogus' in m for m in self.levels(issues, checks.WARNING)))

    def test_broken_template_is_reported_not_raised(self):
        issues = self.run_checks(project('WEAPON_NOPE'), ['w_ar_testgun.ydr'])
        self.assertTrue(checks.has_errors(issues))


if __name__ == '__main__':
    unittest.main()
