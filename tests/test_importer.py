"""テンプレートの取り込みと、武器ごとの取り付けボーンのテスト。"""
from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from kn_weapontoolkit import exporter, importer
from kn_weapontoolkit.model import ComponentSpec, Project
from kn_weapontoolkit.templates import TemplateLibrary, bone_family, find_weapon_item
from kn_weapontoolkit.xmlio import parse_bytes

ROOT = Path(__file__).resolve().parent.parent
BUNDLED = ROOT / 'templates'

WEAPONS_META = '''<?xml version="1.0" encoding="UTF-8"?>
<CWeaponInfoBlob>
  <SlotNavigateOrder><Item><WeaponSlots>
    <Item><OrderNumber value="512" /><Entry>SLOT_TESTRIFLE</Entry></Item>
    <Item><OrderNumber value="513" /><Entry>SLOT_TESTPISTOL</Entry></Item>
  </WeaponSlots></Item></SlotNavigateOrder>
  <Infos><Item><Infos>
    <Item type="CAmmoInfo"><Name>AMMO_TEST</Name></Item>
    <Item type="CWeaponInfo">
      <Name>WEAPON_TESTRIFLE</Name><Model>w_ar_testrifle</Model><Audio>AUDIO_ITEM_CARBINERIFLE</Audio>
      <Slot>SLOT_TESTRIFLE</Slot><DamageType>BULLET</DamageType><Group>GROUP_RIFLE</Group>
      <AmmoInfo ref="AMMO_RIFLE" /><ClipSize value="30" /><Damage value="30.000000" />
      <AttachPoints>
        <Item><AttachBone>WAPClip_2</AttachBone><Components>
          <Item><Name>COMPONENT_TESTRIFLE_CLIP_01</Name><Default value="true" /></Item>
        </Components></Item>
        <Item><AttachBone>WAPSupp_3</AttachBone><Components>
          <Item><Name>COMPONENT_AT_AR_SUPP</Name><Default value="false" /></Item>
        </Components></Item>
      </AttachPoints>
      <HumanNameHash>WT_TEST</HumanNameHash><WeaponFlags>CarriedInHand Gun TwoHanded</WeaponFlags>
    </Item>
    <Item type="CWeaponInfo">
      <Name>WEAPON_TESTPISTOL</Name><Model>w_pi_testpistol</Model><Audio /><Slot>SLOT_TESTPISTOL</Slot>
      <DamageType>BULLET</DamageType><Group>GROUP_PISTOL</Group><AmmoInfo ref="AMMO_PISTOL" />
      <HumanNameHash>WT_TEST2</HumanNameHash><WeaponFlags>CarriedInHand Gun</WeaponFlags>
    </Item>
    <Item type="CWeaponInfo"><Name>WEAPON_NOMODEL</Name><Model /><Slot /></Item>
  </Infos></Item></Infos>
  <Name>TEST</Name>
</CWeaponInfoBlob>
'''
COMPONENTS_META = '''<?xml version="1.0" encoding="UTF-8"?>
<CWeaponComponentInfoBlob><Infos>
  <Item type="CWeaponComponentClipInfo"><Name>COMPONENT_TESTRIFLE_CLIP_01</Name><Model>w_ar_testrifle_mag1</Model>
    <AttachBone>AAPClip</AttachBone><ClipSize value="30" /></Item>
  <Item type="CWeaponComponentSuppressorInfo"><Name>COMPONENT_TEST_ORPHAN</Name><Model>w_at_orphan</Model>
    <AttachBone>AAPSupp</AttachBone></Item>
</Infos><InfoBlobName /></CWeaponComponentInfoBlob>
'''
ANIMS_META = '''<?xml version="1.0" encoding="UTF-8"?>
<CWeaponAnimationsSets><WeaponAnimationsSets>
  <Item key="Default"><WeaponAnimations>
    <Item key="WEAPON_TESTRIFLE"><MotionClipSetHash>move_test</MotionClipSetHash>
      <AnimFireRateModifier value="1.000000" /></Item>
    <Item key="WEAPON_OTHER"><MotionClipSetHash>move_other</MotionClipSetHash></Item>
  </WeaponAnimations></Item>
  <Item key="FirstPerson"><Fallback>Default</Fallback><WeaponAnimations>
    <Item key="WEAPON_TESTRIFLE"><MotionClipSetHash>move_fps</MotionClipSetHash></Item>
  </WeaponAnimations></Item>
</WeaponAnimationsSets></CWeaponAnimationsSets>
'''
PERSONALITY_META = '''<?xml version="1.0" encoding="UTF-8"?>
<CPedModelInfo__PersonalityDataList><MovementModeUnholsterData>
  <Item><Name>UNHOLSTER_UNARMED</Name><UnholsterClips><Item>
    <Weapons><Item>WEAPON_TESTRIFLE</Item></Weapons><Clip>unarmed_holster_2h</Clip>
  </Item></UnholsterClips></Item>
</MovementModeUnholsterData><MovementModes /></CPedModelInfo__PersonalityDataList>
'''
# 全武器入りの大きいファイル(専用ではない)
BIG_PERSONALITY = PERSONALITY_META.replace(
    '<Item>WEAPON_TESTRIFLE</Item>',
    '<Item>WEAPON_TESTRIFLE</Item><Item>WEAPON_A</Item><Item>WEAPON_B</Item><Item>WEAPON_C</Item>')


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding='utf-8')


class ImporterTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.src = base / '取り込み 元' / 'my_weapons'
        self.user = base / 'user templates'
        write(self.src / 'meta' / 'weapons.meta', WEAPONS_META)
        write(self.src / 'meta' / 'weaponcomponents.meta', COMPONENTS_META)
        write(self.src / 'meta' / 'weaponanimations.meta', ANIMS_META)
        write(self.src / 'meta' / 'pedpersonality.meta', PERSONALITY_META)
        write(self.src / 'meta' / 'broken.meta', '<not closed>')
        write(self.src / 'meta' / 'notes.xml', '<Something />')       # 関係ない XML は無視する
        (self.src / 'stream').mkdir()
        (self.src / 'stream' / 'w_ar_testrifle.ydr').write_bytes(b'RSC7')
        self.lib = TemplateLibrary([self.user, BUNDLED])

    def test_scan(self):
        idx = importer.MetaIndex.scan([self.src])
        self.assertEqual(set(idx.weapons), {'WEAPON_TESTRIFLE', 'WEAPON_TESTPISTOL', 'WEAPON_NOMODEL'})
        self.assertEqual([w.name for w in idx.importable_weapons()], ['WEAPON_TESTPISTOL', 'WEAPON_TESTRIFLE'])
        self.assertEqual(set(idx.components), {'COMPONENT_TESTRIFLE_CLIP_01', 'COMPONENT_TEST_ORPHAN'})
        self.assertEqual(len(idx.unreadable), 1)
        self.assertEqual(idx.weapons['WEAPON_TESTRIFLE'].order, '512')
        self.assertEqual(idx.bone_counts()['COMPONENT_TESTRIFLE_CLIP_01'].most_common(1)[0][0], 'WAPClip_2')

    def test_import_and_use(self):
        idx = importer.MetaIndex.scan([self.src])
        failed = importer.import_into(idx, self.user, self.lib, ['WEAPON_TESTRIFLE', 'WEAPON_TESTPISTOL'],
                                      ['COMPONENT_TESTRIFLE_CLIP_01', 'COMPONENT_TEST_ORPHAN'])
        self.assertEqual(failed, [])
        self.assertIn('WEAPON_TESTRIFLE', self.lib.weapon_names())
        self.assertIn('WEAPON_PISTOL', self.lib.weapon_names())          # 同梱分も並ぶ
        rifle = self.lib.weapon('WEAPON_TESTRIFLE')
        self.assertEqual(rifle.source, 'user')
        self.assertEqual(self.lib.weapon('WEAPON_PISTOL').source, 'bundled')
        # 専用の動作・構え方はそのまま使い、テンプレートの武器定義からバニラの部品は外す
        self.assertEqual(rifle.info['animations'], 'own')
        self.assertEqual(rifle.info['personality'], 'own')
        self.assertEqual(rifle.attach_points, [])
        self.assertEqual(rifle.vanilla_attach_points()[0][0], 'WAPClip_2')
        anim = rifle.animations_root()
        self.assertEqual([i.get('key') for i in anim.iter('Item') if i.get('key', '').startswith('WEAPON_')],
                         ['WEAPON_TESTRIFLE', 'WEAPON_TESTRIFLE'])
        self.assertEqual(anim.find('WeaponAnimationsSets/Item[@key="FirstPerson"]/Fallback').text, 'Default')
        # 動作の無い武器は近い武器から借りる(拳銃 → WEAPON_PISTOL)
        pistol = self.lib.weapon('WEAPON_TESTPISTOL')
        self.assertEqual(pistol.borrowed('animations'), 'WEAPON_PISTOL')
        keys = {i.get('key') for i in pistol.animations_root().iter('Item') if i.get('key', '').startswith('WEAPON_')}
        self.assertEqual(keys, {'WEAPON_TESTPISTOL'})
        self.assertEqual({i.text for w in pistol.personality_root().iter('Weapons') for i in w}, {'WEAPON_TESTPISTOL'})
        # 部品: 武器側で実際に使われているボーン / 使われていなければ推測
        self.assertEqual(self.lib.component('COMPONENT_TESTRIFLE_CLIP_01').weapon_bone, 'WAPClip_2')
        self.assertEqual(self.lib.component('COMPONENT_TEST_ORPHAN').weapon_bone, 'WAPSupp')
        # 取り込んだテンプレートで書き出せる。部品は武器のバニラ定義どおりのボーンに付く
        p = Project(template='WEAPON_TESTRIFLE', weapon_id='WEAPON_MINE', model='w_ar_mine', components=[
            ComponentSpec(template='COMPONENT_TESTRIFLE_CLIP_01', name='COMPONENT_MINE_CLIP', default=True),
            ComponentSpec(template='COMPONENT_AT_AR_SUPP', name='COMPONENT_MINE_SUPP')])
        res = exporter.build(p, self.lib, [])
        item = find_weapon_item(parse_bytes(res.files['meta/weapons.meta']), 'WEAPON_MINE')
        self.assertEqual(item.findtext('Name'), 'WEAPON_MINE')
        bones = [b.text for b in item.findall('AttachPoints/Item/AttachBone')]
        self.assertEqual(bones, ['WAPClip_2', 'WAPSupp_3'])
        order = parse_bytes(res.files['meta/weapons.meta']).find('.//OrderNumber').get('value')
        self.assertEqual(order, '512')

    def test_user_template_overrides_bundled(self):
        idx = importer.MetaIndex.scan([self.src])
        files, info = importer.weapon_template(idx, 'WEAPON_TESTRIFLE', self.lib)
        importer.write_template(self.user / 'weapons' / 'WEAPON_PISTOL', files, info)
        self.lib.reload()
        t = self.lib.weapon('WEAPON_PISTOL')
        self.assertEqual(t.source, 'user')
        self.assertEqual(t.model, 'w_ar_testrifle')
        self.assertEqual(self.lib.weapon_names().count('WEAPON_PISTOL'), 1)

    def test_big_personality_is_cut(self):
        # 他の武器も挙げている大きいファイルは丸ごと使わず、その武器の項目だけを切り出す
        write(self.src / 'meta' / 'pedpersonality.meta', BIG_PERSONALITY)
        idx = importer.MetaIndex.scan([self.src])
        cut = idx.own_personality('WEAPON_TESTRIFLE')
        self.assertIsNotNone(cut)
        self.assertIsNot(cut, idx.personalities[0][1])
        files, info = importer.weapon_template(idx, 'WEAPON_TESTRIFLE', self.lib, 'WEAPON_CARBINERIFLE')
        self.assertEqual(info['personality'], 'own')
        self.assertEqual({i.text for w in files['pedpersonality.meta'].iter('Weapons') for i in w}, {'WEAPON_TESTRIFLE'})
        self.assertIsNone(idx.own_personality('WEAPON_TESTPISTOL'))     # 挙げられていない武器は借りる

    def test_write_template_replaces_atomically(self):
        idx = importer.MetaIndex.scan([self.src])
        dest = self.user / 'components' / 'COMPONENT_TEST_ORPHAN'
        importer.write_template(dest, {'weaponcomponents.meta': importer.component_template(idx, 'COMPONENT_TEST_ORPHAN')})
        (dest / 'stale.txt').write_text('old')
        importer.write_template(dest, {'weaponcomponents.meta': importer.component_template(idx, 'COMPONENT_TEST_ORPHAN')})
        self.assertEqual(sorted(p.name for p in dest.iterdir()), ['weaponcomponents.meta'])
        self.assertEqual([p.name for p in dest.parent.iterdir()], ['COMPONENT_TEST_ORPHAN'])

    def test_duplicate_animation_sets(self):
        # 本体(common.rpf)とタイトルアップデート(update.rpf)の両方から書き出した場合、セットは重複させない
        write(self.src.parent / 'common.rpf' / 'weaponanimations.meta', ANIMS_META.replace('move_test', 'move_old'))
        write(self.src.parent / 'update' / 'update.rpf' / 'weaponanimations.meta', ANIMS_META)
        idx = importer.MetaIndex.scan([self.src.parent])
        own = idx.own_animations('WEAPON_TESTRIFLE')
        self.assertEqual([a.get('key') for a, _ in own], ['Default', 'FirstPerson'])
        self.assertEqual(own[0][1].findtext('MotionClipSetHash'), 'move_test')

    def test_priority(self):
        self.assertGreater(importer.path_priority('x/update/update.rpf/dlc_patch/a/w.meta'),
                           importer.path_priority('x/update/x64/dlcpacks/a/dlc.rpf/w.meta'))
        self.assertGreater(importer.path_priority('x/update/x64/dlcpacks/a/w.meta'),
                           importer.path_priority('x/x64w.rpf/dlcpacks/a/w.meta'))
        self.assertGreater(importer.path_priority('x/x64w.rpf/dlcpacks/a/w.meta'),
                           importer.path_priority('x/update/update.rpf/common/data/ai/weapons.meta'))
        self.assertGreater(importer.path_priority('x/update/update.rpf/common/data/ai/weaponanimations.meta'),
                           importer.path_priority('x/common.rpf/data/ai/weaponanimations.meta'))
        # 同じ優先度なら後に読んだファイル(名前順で後 = 新しい版)が勝つ
        write(self.src / 'meta' / 'z_newer.meta', COMPONENTS_META.replace('w_ar_testrifle_mag1', 'newer_mag'))
        idx = importer.MetaIndex.scan([self.src])
        self.assertEqual(idx.components['COMPONENT_TESTRIFLE_CLIP_01'].item.findtext('Model'), 'newer_mag')


class DonorAndBoneTest(unittest.TestCase):
    LIB = TemplateLibrary(BUNDLED)

    def test_choose_donor(self):
        idx = importer.MetaIndex()
        mk = lambda name, group, two: importer.FoundWeapon(name, parse_bytes(
            f'<Item type="CWeaponInfo"><Name>{name}</Name><Model>m</Model><Group>{group}</Group>'
            f'<WeaponFlags>{"TwoHanded" if two else ""}</WeaponFlags></Item>'.encode()), 'x')
        self.assertEqual(importer.choose_donor(mk('WEAPON_FOO_MK2', 'GROUP_RIFLE', True), self.LIB),
                         'WEAPON_CARBINERIFLE')      # WEAPON_FOO が無ければ種類で決める
        self.assertEqual(importer.choose_donor(mk('WEAPON_SMG_MK2', 'GROUP_SMG', True), self.LIB), 'WEAPON_SMG')
        self.assertEqual(importer.choose_donor(mk('WEAPON_X', 'GROUP_MELEE', True), self.LIB), 'WEAPON_BAT')
        self.assertEqual(importer.choose_donor(mk('WEAPON_X', 'GROUP_MELEE', False), self.LIB), 'WEAPON_HAMMER')
        self.assertEqual(importer.choose_donor(mk('WEAPON_X', 'GROUP_UNKNOWN', False), self.LIB), '')
        self.assertEqual(importer.choose_donor(mk('WEAPON_DAGGER', 'GROUP_MELEE', False), self.LIB), 'WEAPON_KNIFE')
        del idx

    def test_bone_family(self):
        self.assertEqual(bone_family('WAPSupp_2'), 'WAPSupp')
        self.assertEqual(bone_family('WAPFlshLasr'), 'WAPFlshLasr')

    def test_bones_follow_template_weapon(self):
        # バニラのデータどおり: MK2 系はマズルを WAPSupp_2 に付ける
        cases = [('WEAPON_CARBINERIFLE_MK2', 'COMPONENT_AT_MUZZLE_01', 'WAPSupp_2'),
                 ('WEAPON_CARBINERIFLE', 'COMPONENT_AT_AR_SUPP', 'WAPSupp'),
                 ('WEAPON_CARBINERIFLE_MK2', 'COMPONENT_AT_AR_SUPP', 'WAPSupp_2'),     # 同じ役割のボーンに合わせる
                 ('WEAPON_COMBATPDW', 'COMPONENT_COMBATPDW_CLIP_01', 'WAPClip_2'),
                 ('WEAPON_KNIFE', 'COMPONENT_AT_AR_SUPP', 'WAPSupp')]                 # 手がかりが無ければ部品の既定
        for w, c, want in cases:
            with self.subTest(weapon=w, component=c):
                got = exporter.component_bone(ComponentSpec(template=c), self.LIB.component(c), self.LIB.weapon(w))
                self.assertEqual(got, want)
        manual = ComponentSpec(template='COMPONENT_AT_AR_SUPP', bone='WAPSupp_9')
        self.assertEqual(exporter.component_bone(manual, self.LIB.component('COMPONENT_AT_AR_SUPP'),
                                                 self.LIB.weapon('WEAPON_CARBINERIFLE_MK2')), 'WAPSupp_9')

    def test_bundled_template_info(self):
        for name in self.LIB.weapon_names():
            t = self.LIB.weapon(name)
            self.assertIn('source', t.info, name)
            for kind in ('animations', 'personality'):
                donor = t.borrowed(kind)
                if donor:
                    self.assertIn(donor, self.LIB.weapon_names(), name)
        info = json.loads((BUNDLED / 'weapons' / 'WEAPON_HEAVYSNIPER_MK2' / 'template.json').read_text(encoding='utf-8'))
        self.assertEqual(info['animations'], 'borrowed:WEAPON_HEAVYSNIPER')


if __name__ == '__main__':
    unittest.main()


FULL_PERSONALITY = '''<?xml version="1.0" encoding="UTF-8"?>
<CPedModelInfo__PersonalityDataList>
  <MovementModeUnholsterData>
    <Item><Name>UNHOLSTER_UNARMED</Name><UnholsterClips>
      <Item><Weapons><Item>WEAPON_PISTOL</Item><Item>WEAPON_COMBATPISTOL</Item></Weapons><Clip>a</Clip></Item>
      <Item><Weapons><Item>WEAPON_FIREEXTINGUISHER</Item></Weapons><Clip>ext</Clip></Item>
    </UnholsterClips></Item>
    <Item><Name>UNHOLSTER_2H</Name><UnholsterClips>
      <Item><Weapons><Item>WEAPON_RPG</Item></Weapons><Clip>b</Clip></Item>
    </UnholsterClips></Item>
  </MovementModeUnholsterData>
  <MovementModes>
    <Item><Name>DEFAULT_ACTION</Name><MovementModes>
      <Item>
        <Item><Weapons><Item>WEAPON_PISTOL</Item></Weapons><ClipSets /></Item>
        <Item><Weapons><Item>WEAPON_PETROLCAN</Item><Item>WEAPON_FIREEXTINGUISHER</Item></Weapons><ClipSets /></Item>
      </Item>
      <Item>
        <Item><Weapons><Item>WEAPON_PISTOL</Item></Weapons><ClipSets /></Item>
      </Item>
    </MovementModes><LastBattleEventHighEnergyStartTime value="0.0" /></Item>
    <Item><Name>MP_FEMALE_ACTION</Name><MovementModes>
      <Item><Item><Weapons><Item>WEAPON_RPG</Item></Weapons><ClipSets /></Item></Item>
    </MovementModes></Item>
  </MovementModes>
  <PedPersonalities><Item><Name>SOMEONE</Name></Item></PedPersonalities>
</CPedModelInfo__PersonalityDataList>
'''


class PersonalityCutTest(unittest.TestCase):
    def test_cut_from_full_file(self):
        root = parse_bytes(FULL_PERSONALITY.encode())
        cut = importer.filter_personality(root, 'WEAPON_FIREEXTINGUISHER')
        self.assertEqual([c.tag for c in cut], ['MovementModeUnholsterData', 'MovementModes'])   # 他の節は持ち込まない
        unh = cut.findall('MovementModeUnholsterData/Item')
        self.assertEqual([u.findtext('Name') for u in unh], ['UNHOLSTER_UNARMED'])
        self.assertEqual([c.findtext('Clip') for c in unh[0].findall('UnholsterClips/Item')], ['ext'])
        modes = cut.findall('MovementModes/Item')
        self.assertEqual([m.findtext('Name') for m in modes], ['DEFAULT_ACTION'])
        arrays = modes[0].findall('MovementModes/Item')
        self.assertEqual(len(arrays), 2)                    # 配列の位置は残す
        self.assertEqual(len(arrays[0].findall('Item')), 1)
        self.assertEqual(arrays[1].findall('Item'), [])
        self.assertIsNotNone(modes[0].find('LastBattleEventHighEnergyStartTime'))
        self.assertIsNone(importer.filter_personality(root, 'WEAPON_NOTHING'))
        # 元の要素は書き換えない
        self.assertEqual(len(root.findall('MovementModeUnholsterData/Item')), 2)

    def test_index_uses_cut(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / 'pedpersonality.meta', FULL_PERSONALITY)
            idx = importer.MetaIndex.scan([d])
            got = idx.own_personality('WEAPON_PETROLCAN')
            self.assertIsNotNone(got)
            self.assertEqual([m.findtext('Name') for m in got.findall('MovementModes/Item')], ['DEFAULT_ACTION'])
            self.assertEqual(got.findall('MovementModeUnholsterData/Item'), [])
