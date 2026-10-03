"""推測(suggest)と設定のテスト。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kn_weapontoolkit import assets, suggest
from kn_weapontoolkit.model import ComponentSpec, Project
from kn_weapontoolkit.settings import FIRST_SLOT, Settings
from kn_weapontoolkit.templates import TemplateLibrary

LIB = TemplateLibrary(Path(__file__).resolve().parent.parent / 'templates')


def fake(names: list[str]) -> list[assets.Asset]:
    return [assets.Asset(n, Path(n)) for n in names]


class SuggestTest(unittest.TestCase):
    def test_guess_weapon_model(self):
        g = suggest.guess_weapon_model
        self.assertEqual(g(fake(['W_PI_Gun.ydr', 'w_pi_gun_hi.ydr', 'w_pi_gun.ytd'])), 'w_pi_gun')
        self.assertEqual(g(fake(['w_ar_m4.ydr', 'w_ar_m4_mag1.ydr', 'w_ar_m4_supp.ydr', 'prop_other.ydr'])), 'w_ar_m4')
        self.assertEqual(g(fake(['a.ydr', 'b.ydr', 'b_hi.ydr'])), 'b')
        self.assertEqual(g(fake(['a.ydr', 'b.ydr'])), '')       # 決め手が無ければ推測しない
        self.assertEqual(g([]), '')

    def test_suggest_components(self):
        found = fake(['w_ar_m4.ydr', 'w_ar_m4_mag1.ydr', 'w_ar_m4_mag2.ydr', 'w_ar_m4_supp.ydr', 'w_ar_m4_scope.ydr',
                      'w_ar_m4_afgrip.ydr', 'w_ar_m4_flsh.ydr', 'w_ar_m4_strap.ydr', 'w_ar_m4_mag1_hi.ydr'])
        p = Project(template='WEAPON_RPG', weapon_id='WEAPON_M4', model='w_ar_m4')
        got = suggest.suggest_components(p, LIB, found)
        self.assertEqual([(c.name, c.template, c.default) for c in got], [
            ('COMPONENT_M4_GRIP', 'COMPONENT_AT_AR_AFGRIP', False),
            ('COMPONENT_M4_FLSH', 'COMPONENT_AT_AR_FLSH', False),
            ('COMPONENT_M4_CLIP_01', 'COMPONENT_RPG_CLIP_01', True),
            ('COMPONENT_M4_CLIP_02', 'COMPONENT_RPG_CLIP_01', False),     # RPG に CLIP_02 は無い → 01 を流用
            ('COMPONENT_M4_SCOPE', 'COMPONENT_AT_SCOPE_MEDIUM', False),
            ('COMPONENT_M4_SUPP', 'COMPONENT_AT_AR_SUPP', False),
        ])
        # 既にあるモデルは候補に出さない。名前が重なれば番号を足す
        p.components = [ComponentSpec(template='COMPONENT_AT_AR_SUPP', name='COMPONENT_M4_SCOPE', model='w_ar_m4_supp')]
        names = [c.name for c in suggest.suggest_components(p, LIB, found)]
        self.assertNotIn('COMPONENT_M4_SUPP', names)
        self.assertIn('COMPONENT_M4_SCOPE_2', names)

    def test_pistol_templates(self):
        p = Project(template='WEAPON_PISTOL', weapon_id='WEAPON_G17', model='w_pi_g17')
        got = suggest.suggest_components(p, LIB, fake(['w_pi_g17.ydr', 'w_pi_g17_mag1.ydr', 'w_pi_g17_supp.ydr']))
        self.assertEqual([c.template for c in got], ['COMPONENT_PISTOL_CLIP_01', 'COMPONENT_AT_PI_SUPP'])

    def test_auto_component_name(self):
        n = suggest.auto_component_name
        self.assertEqual(n('WEAPON_AK47', 'COMPONENT_BULLPUPRIFLE_CLIP_02'), 'COMPONENT_AK47_CLIP_02')
        self.assertEqual(n('WEAPON_AK47', 'COMPONENT_CARBINERIFLE_BOXMAG'), 'COMPONENT_AK47_BOXMAG')
        self.assertEqual(n('WEAPON_AK47', 'COMPONENT_AT_AR_SUPP'), 'COMPONENT_AK47_AR_SUPP')
        self.assertEqual(n('WEAPON_AK47', 'COMPONENT_AT_AR_SUPP', {'COMPONENT_AK47_AR_SUPP'}), 'COMPONENT_AK47_AR_SUPP_2')
        self.assertEqual(n('', 'COMPONENT_AT_PI_FLSH'), 'COMPONENT_CUSTOM_PI_FLSH')


class SettingsTest(unittest.TestCase):
    def test_slots_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'sub' / 'settings.json'
            s = Settings(path)
            self.assertEqual(s['language'], '')         # 既定は OS の言語に合わせる
            self.assertEqual(s.take_slot(), FIRST_SLOT)
            self.assertEqual(s.take_slot(), FIRST_SLOT + 1)
            s['theme'] = 'light'
            again = Settings(path)
            self.assertEqual(again['next_slot'], FIRST_SLOT + 2)
            self.assertEqual(again['theme'], 'light')

    def test_bad_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'settings.json'
            path.write_text('{"language": "xx", "theme": 5, "next_slot": -3}', encoding='utf-8')
            s = Settings(path)
            self.assertEqual((s['language'], s['theme'], s['next_slot']), ('', 'system', FIRST_SLOT))
            path.write_text('garbage', encoding='utf-8')
            self.assertEqual(Settings(path)['theme'], 'system')


if __name__ == '__main__':
    unittest.main()


class FireTypeCheckTest(unittest.TestCase):
    """発射方式と弾薬の組み合わせの点検(普通の銃からロケットを撃たせる設定など)。"""

    def issues(self, template: str, fields: dict) -> list[str]:
        from kn_weapontoolkit import checks, i18n
        i18n.set_language('ja')
        p = Project(template=template, weapon_id='WEAPON_X', model='w_x', fields=fields)
        return [i.message for i in checks.run(p, LIB, assets.scan('')) if i.level == checks.WARNING]

    def test_combinations(self):
        self.assertFalse([m for m in self.issues('WEAPON_CARBINERIFLE', {}) if '発射方式' in m])
        rocket_rifle = self.issues('WEAPON_CARBINERIFLE', {'FireType': 'PROJECTILE', 'AmmoInfo': 'AMMO_RPG'})
        self.assertFalse([m for m in rocket_rifle if '発射方式' in m])
        half = self.issues('WEAPON_CARBINERIFLE', {'AmmoInfo': 'AMMO_RPG'})
        self.assertTrue(any('PROJECTILE にしてください' in m for m in half))
        wrong = self.issues('WEAPON_CARBINERIFLE', {'FireType': 'PROJECTILE'})
        self.assertTrue(any('飛んでいく弾ではありません' in m for m in wrong))
        spray = self.issues('WEAPON_CARBINERIFLE', {'FireType': 'VOLUMETRIC_PARTICLE'})
        self.assertTrue(any('噴射' in m for m in spray))
        self.assertFalse([m for m in self.issues('WEAPON_RPG', {}) if '発射方式' in m])
        self.assertFalse([m for m in self.issues('WEAPON_GRENADE', {}) if '発射方式' in m])
        # 普通の銃からロケット弾 → 横向きの注意。RPG そのものには出さない
        self.assertTrue(any('横向き' in m for m in rocket_rifle))
        self.assertFalse([m for m in self.issues('WEAPON_RPG', {}) if '横向き' in m])

    def test_explosion_needs_explosive_damage(self):
        bullet = self.issues('WEAPON_CARBINERIFLE', {'Explosion/Default': 'GRENADE'})
        self.assertTrue(any('EXPLOSIVE にしてください' in m for m in bullet))
        ok = self.issues('WEAPON_CARBINERIFLE', {'Explosion/Default': 'GRENADE', 'DamageType': 'EXPLOSIVE'})
        self.assertFalse([m for m in ok if 'EXPLOSIVE にしてください' in m])
        self.assertFalse([m for m in self.issues('WEAPON_RAILGUN', {}) if 'EXPLOSIVE にしてください' in m])
        self.assertFalse([m for m in self.issues('WEAPON_CARBINERIFLE', {}) if 'EXPLOSIVE にしてください' in m])

    def test_time_between_shots_warning(self):
        msg = '射撃間隔を変えても'
        self.assertTrue(any(msg in m for m in self.issues('WEAPON_CARBINERIFLE', {'TimeBetweenShots': '0.4'})))
        self.assertFalse([m for m in self.issues('WEAPON_CARBINERIFLE', {'TimeBetweenShots': '0.135000'}) if msg in m])
        self.assertTrue(any(msg in m for m in self.issues('WEAPON_PISTOL', {'TimeBetweenShots': '0.2'})))   # 単発でも効かなかった
        self.assertFalse([m for m in self.issues('WEAPON_PISTOL', {}) if msg in m])

    def test_nested_fields_listed(self):
        tags = [f.tag for f in LIB.weapon('WEAPON_RPG').fields]
        self.assertIn('Fx/FlashFx', tags)
        self.assertIn('Explosion/Default', tags)
        self.assertNotIn('Name', tags)
        self.assertFalse([t for t in tags if t.count('/') > 1])


class AutoScrollMathTest(unittest.TestCase):
    """ホイールを押したまま動かして送るときの速さ。"""

    def test_step(self):
        from kn_weapontoolkit import autoscroll as a
        self.assertEqual(a.step(0), 0.0)
        self.assertEqual(a.step(a.DEAD_ZONE), 0.0)          # 遊びの中は動かない
        self.assertEqual(a.step(-a.DEAD_ZONE), 0.0)
        self.assertGreater(a.step(a.DEAD_ZONE + 10), 0)     # 下へ動かせば下へ
        self.assertLess(a.step(-a.DEAD_ZONE - 10), 0)
        self.assertGreater(a.step(200), a.step(50))          # 離すほど速い
        self.assertEqual(a.step(100000), a.MAX_STEP)         # 上限で頭打ち
        self.assertEqual(a.step(-100000), -a.MAX_STEP)

    def test_accumulator(self):
        from kn_weapontoolkit import autoscroll as a
        acc = a.Accumulator()
        self.assertEqual([acc.take(0.4) for _ in range(5)], [0, 0, 1, 0, 1])   # 端数を持ち越す
        acc = a.Accumulator()
        self.assertEqual(sum(acc.take(-7.0, unit=20.0) for _ in range(10)), -3)  # 1行=20px の一覧で -70px
        acc = a.Accumulator()
        self.assertEqual(acc.take(5.0, unit=0.0), 5)                          # 単位 0 でも割り算で落ちない
