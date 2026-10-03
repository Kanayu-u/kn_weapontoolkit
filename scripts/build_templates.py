"""同梱テンプレートを公開されている meta から増やす(開発者用・一度だけ実行)。

    python scripts/build_templates.py <バニラの weapon*.meta のフォルダ> <バニラの weaponcomponents のフォルダ>

- 新しい武器: NEW_WEAPONS。動作・構え方は importer.DONORS / GROUP_DONORS の近い武器から借りる
- 新しい部品: まだテンプレートに無い COMPONENT_* を全部
- 既存の武器テンプレート: template.json にバニラの取り付けボーンを記録する(meta は変えない)
出どころは THIRD_PARTY_NOTICES.md に書く。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kn_weapontoolkit import importer  # noqa: E402
from kn_weapontoolkit.templates import TEMPLATE_INFO, TemplateLibrary  # noqa: E402

# プレイヤーが持てる武器のうち、まだテンプレートが無いもの。
# 除外: ミニガン系(近い動作を持つテンプレートが無い)、ミッション用の道具・缶・動物・乗り物の武器・ダメージ種別
NEW_WEAPONS = [
    'WEAPON_AUTOSHOTGUN', 'WEAPON_BATTLEAXE', 'WEAPON_BATTLERIFLE', 'WEAPON_BOTTLE', 'WEAPON_BULLPUPRIFLE_MK2',
    'WEAPON_BULLPUPSHOTGUN', 'WEAPON_BZGAS', 'WEAPON_CANDYCANE', 'WEAPON_CERAMICPISTOL', 'WEAPON_COMBATMG_MK2',
    'WEAPON_COMPACTLAUNCHER', 'WEAPON_DAGGER', 'WEAPON_EMPLAUNCHER', 'WEAPON_FIREWORK', 'WEAPON_FLARE',
    'WEAPON_FLAREGUN', 'WEAPON_FLASHLIGHT', 'WEAPON_GRENADE', 'WEAPON_GRENADELAUNCHER_SMOKE', 'WEAPON_HEAVYSNIPER_MK2',
    'WEAPON_MARKSMANPISTOL', 'WEAPON_MARKSMANRIFLE_MK2', 'WEAPON_MILITARYRIFLE', 'WEAPON_MOLOTOV',
    'WEAPON_NAVYREVOLVER', 'WEAPON_PUMPSHOTGUN_MK2', 'WEAPON_RAILGUN', 'WEAPON_RAYPISTOL', 'WEAPON_REVOLVER_MK2',
    'WEAPON_SMOKEGRENADE', 'WEAPON_SNOWLAUNCHER', 'WEAPON_SNSPISTOL_MK2', 'WEAPON_SPECIALCARBINE_MK2',
    'WEAPON_STICKYBOMB', 'WEAPON_STONE_HATCHET', 'WEAPON_STRICKLER', 'WEAPON_STUNGUN_MP', 'WEAPON_WRENCH',
]
BUNDLED_SOURCE = 'vWeaponsToolkit / FiveM Addon Weapon Tool Kit'


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    idx = importer.MetaIndex.scan([Path(a) for a in sys.argv[1:]])
    lib = TemplateLibrary(ROOT / 'templates')
    print(f'read {idx.files} files, weapons {len(idx.weapons)}, components {len(idx.components)}, '
          f'unreadable {len(idx.unreadable)}')

    # 既存の武器テンプレートに、バニラの取り付けボーンを記録する
    # 既にある記録(借りた動作 'animations' / 'personality' など)は残し、取り付けボーンだけ足す
    for name in lib.weapon_names():
        t = lib.weapon(name)
        w = idx.weapons.get(t.internal_name)
        info = dict(t.info)
        info.setdefault('source', BUNDLED_SOURCE)
        info['attach_points'] = w.attach_points() if w else info.get('attach_points', [])
        (t.dir / TEMPLATE_INFO).write_text(json.dumps(info, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    bones = idx.bone_counts()
    existing = {lib.component(n).internal_name.upper() for n in lib.component_names()} | set(lib.component_names())
    added_c = 0
    for c in idx.importable_components():
        if not c.name.startswith('COMPONENT_') or c.name in existing:
            continue
        importer.write_template(ROOT / 'templates' / 'components' / c.name,
                                {'weaponcomponents.meta': importer.component_template(idx, c.name, bones)})
        added_c += 1

    added_w = []
    for name in NEW_WEAPONS:
        if name in lib.weapon_names():
            continue
        donor = importer.choose_donor(idx.weapons[name], lib)
        files, info = importer.weapon_template(idx, name, lib, donor)
        importer.write_template(ROOT / 'templates' / 'weapons' / name, files, info)
        added_w.append((name, donor, info.get('animations'), info.get('personality')))
    for row in added_w:
        print('weapon', *row)
    print(f'added weapons {len(added_w)}, components {added_c}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
