"""meta ファイル群からテンプレートを切り出す(テンプレートの取り込み)。

対象は OpenIV / CodeWalker で書き出したバニラの meta や、手持ちのアドオン武器リソース。フォルダ以下の
.meta / .xml を読み、ファイル名ではなく中身(ルート要素)で種類を見分ける。

- 武器: CWeaponInfo 1つと、その武器のスロットの並び定義だけを残した weapons.meta を作る
- 動作(weaponanimations)・構え方(pedpersonality): その武器の分が見つからなければ、近い武器のテンプレートから
  借りる(借りたことは template.json に記録する)
- 部品: 定義を1つずつ切り出し、武器側の AttachPoints から実際の取り付けボーンを記録する
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .templates import TEMPLATE_INFO, TemplateLibrary, find_weapon_item, infer_weapon_bone
from .xmlio import MetaError, dumps, elements, parse_file, text_of

META_SUFFIXES = ('.meta', '.xml')
MAX_META_BYTES = 64 * 1024 * 1024
MAX_META_FILES = 5000         # 誤ってドライブ直下などを選んだときの歯止め(GTA の全 meta を書き出しても数百個)
MAX_VISITED = 200000          # meta 以外も含めて見たファイル数の上限
_NAME_OK = re.compile(r'^[A-Za-z0-9_]+$')

# 近い武器(動作・構え方を借りる先)。MK2 は元の武器、それ以外は種類と持ち方で決める
DONORS = {
    'WEAPON_AUTOSHOTGUN': 'WEAPON_ASSAULTSHOTGUN', 'WEAPON_BULLPUPSHOTGUN': 'WEAPON_PUMPSHOTGUN',
    'WEAPON_BATTLERIFLE': 'WEAPON_ASSAULTRIFLE', 'WEAPON_MILITARYRIFLE': 'WEAPON_BULLPUPRIFLE',
    'WEAPON_STRICKLER': 'WEAPON_BULLPUPRIFLE', 'WEAPON_NAVYREVOLVER': 'WEAPON_REVOLVER',
    'WEAPON_STUNGUN_MP': 'WEAPON_STUNGUN', 'WEAPON_GRENADELAUNCHER_SMOKE': 'WEAPON_GRENADELAUNCHER',
    'WEAPON_FIREWORK': 'WEAPON_RPG', 'WEAPON_RAILGUN': 'WEAPON_RAILGUNXM3',
    'WEAPON_BATTLEAXE': 'WEAPON_HATCHET', 'WEAPON_STONE_HATCHET': 'WEAPON_HATCHET', 'WEAPON_BOTTLE': 'WEAPON_KNIFE',
    'WEAPON_DAGGER': 'WEAPON_KNIFE', 'WEAPON_FLASHLIGHT': 'WEAPON_NIGHTSTICK', 'WEAPON_WRENCH': 'WEAPON_HAMMER',
    'WEAPON_CANDYCANE': 'WEAPON_HAMMER',
}
# 種類ごとの既定 (片手, 両手)
GROUP_DONORS = {
    'GROUP_PISTOL': ('WEAPON_PISTOL', 'WEAPON_PISTOL'), 'GROUP_SMG': ('WEAPON_MICROSMG', 'WEAPON_SMG'),
    'GROUP_RIFLE': ('WEAPON_COMPACTRIFLE', 'WEAPON_CARBINERIFLE'), 'GROUP_MG': ('WEAPON_MG', 'WEAPON_MG'),
    'GROUP_SHOTGUN': ('WEAPON_SAWNOFFSHOTGUN', 'WEAPON_PUMPSHOTGUN'),
    'GROUP_SNIPER': ('WEAPON_SNIPERRIFLE', 'WEAPON_SNIPERRIFLE'), 'GROUP_HEAVY': ('WEAPON_PISTOL', 'WEAPON_RPG'),
    'GROUP_THROWN': ('WEAPON_PIPEBOMB', 'WEAPON_PIPEBOMB'), 'GROUP_MELEE': ('WEAPON_HAMMER', 'WEAPON_BAT'),
    'GROUP_STUNGUN': ('WEAPON_STUNGUN', 'WEAPON_STUNGUN'),
}


def path_priority(path: str) -> int:
    """同じ名前の定義が複数あるときの優先度。ゲームの読み込み順(後のパッチが勝つ)に合わせる。"""
    p = path.replace('\\', '/').lower()
    if '/dlc_patch/' in p:
        return 4
    if '/update/x64/dlcpacks/' in p:
        return 3
    if '/dlcpacks/' in p:
        return 2
    if 'update.rpf' in p:       # タイトルアップデートは common.rpf の同名ファイルより優先
        return 1
    return 0


@dataclass
class FoundWeapon:
    name: str
    item: ET.Element
    source: str
    order: str = ''         # SlotNavigateOrder の OrderNumber
    priority: int = 0

    @property
    def group(self) -> str:
        return text_of(self.item.find('Group'))

    @property
    def model(self) -> str:
        return text_of(self.item.find('Model'))

    @property
    def two_handed(self) -> bool:
        return 'TwoHanded' in text_of(self.item.find('WeaponFlags')).split()

    def attach_points(self) -> list[tuple[str, list[str]]]:
        out = []
        for p in self.item.findall('AttachPoints/Item'):
            out.append((text_of(p.find('AttachBone')), [text_of(c.find('Name')) for c in p.findall('Components/Item')]))
        return out


@dataclass
class FoundComponent:
    name: str
    item: ET.Element
    source: str
    priority: int = 0


@dataclass
class MetaIndex:
    weapons: dict[str, FoundWeapon] = field(default_factory=dict)
    components: dict[str, FoundComponent] = field(default_factory=dict)
    # 武器名(大文字) → {セット名: (優先度, 読んだ順, セットの要素, その武器の Item)}
    animations: dict[str, dict[str, tuple[int, int, ET.Element, ET.Element]]] = field(default_factory=dict)
    personalities: list[tuple[str, ET.Element]] = field(default_factory=list)
    unreadable: list[tuple[str, str]] = field(default_factory=list)
    files: int = 0
    truncated: bool = False     # 多すぎて途中で探すのをやめた

    # --- 読み込み
    @classmethod
    def scan(cls, folders: list[str | Path]) -> 'MetaIndex':
        idx = cls()
        paths: list[Path] = []
        visited = 0
        for folder in folders:
            for cur, dirs, files in os.walk(folder):
                dirs.sort(key=str.lower)
                visited += len(files)
                paths += [Path(cur) / f for f in sorted(files, key=str.lower) if f.lower().endswith(META_SUFFIXES)]
                if visited > MAX_VISITED or len(paths) > MAX_META_FILES:
                    idx.truncated = True
                    break
            if idx.truncated:
                break
        for p in paths[:MAX_META_FILES]:
            idx._add_file(p)
        return idx

    def _add_file(self, path: Path) -> None:
        try:
            if path.stat().st_size > MAX_META_BYTES:
                self.unreadable.append((str(path), 'too large'))
                return
            root = parse_file(path)
        except (OSError, MetaError) as e:
            self.unreadable.append((str(path), str(e)))
            return
        self.files += 1
        src = str(path)
        prio = path_priority(src)
        if root.tag == 'CWeaponInfoBlob':
            self._add_weapons(root, src, prio)
        elif root.tag == 'CWeaponComponentInfoBlob':
            for it in root.findall('Infos/Item'):
                name = text_of(it.find('Name'))
                old = self.components.get(name)
                if name and (old is None or prio >= old.priority):     # 同じ優先度なら後のファイル(新しい版)
                    self.components[name] = FoundComponent(name, it, src, prio)
        elif root.tag == 'CWeaponAnimationsSets':
            # 本体とパッチの両方に同じセットがあれば、優先度の高い方(同じなら後に読んだ方)を使う
            for aset in root.findall('WeaponAnimationsSets/Item'):
                for it in aset.findall('WeaponAnimations/Item'):
                    key = it.get('key', '').upper()
                    if not key:
                        continue
                    sets = self.animations.setdefault(key, {})
                    set_key = aset.get('key', '')
                    old = sets.get(set_key)
                    if old is None or (prio, self.files) >= old[:2]:
                        sets[set_key] = (prio, self.files, aset, it)
        elif root.tag == 'CPedModelInfo__PersonalityDataList':
            self.personalities.append((src, root))

    def _add_weapons(self, root: ET.Element, src: str, prio: int) -> None:
        orders: dict[str, str] = {}
        for slot in root.findall('SlotNavigateOrder/Item/WeaponSlots/Item'):
            entry = text_of(slot.find('Entry'))
            order = slot.find('OrderNumber')
            if entry and order is not None and entry not in orders:
                orders[entry] = order.get('value', '')
        for it in root.iter('Item'):
            if it.get('type') != 'CWeaponInfo':
                continue
            name = text_of(it.find('Name'))
            old = self.weapons.get(name)
            if name and (old is None or prio >= old.priority):
                self.weapons[name] = FoundWeapon(name, it, src, orders.get(text_of(it.find('Slot')), ''), prio)

    # --- 調べる
    def bone_counts(self) -> dict[str, Counter]:
        """部品名 → 取り付けボーンの出現数(全武器の AttachPoints から)。"""
        out: dict[str, Counter] = {}
        for w in self.weapons.values():
            for bone, comps in w.attach_points():
                for c in comps:
                    out.setdefault(c, Counter())[bone] += 1
        return out

    def importable_weapons(self) -> list[FoundWeapon]:
        """取り込める武器(モデルのあるもの)。乗り物の武器・ダメージ種別などはモデルが無いので除かれる。"""
        return sorted((w for w in self.weapons.values() if w.model and _NAME_OK.match(w.name)), key=lambda w: w.name)

    def importable_components(self) -> list[FoundComponent]:
        return sorted((c for c in self.components.values() if _NAME_OK.match(c.name)), key=lambda c: c.name)

    def own_animations(self, name: str) -> list[tuple[ET.Element, ET.Element]]:
        """その武器の動作 [(セット, Item)]。セットは最初に見つけた順。"""
        return [(aset, it) for _p, _o, aset, it in self.animations.get(name.upper(), {}).values()]

    def own_personality(self, name: str) -> ET.Element | None:
        """その武器の構え方。専用のファイル(武器名が3種類以下)があればそれ、無ければ全武器入りのファイルから
        その武器の項目だけを切り出す。見つからなければ None。"""
        for _src, root in self.personalities:
            names = {text_of(i).upper() for w in root.iter('Weapons') for i in elements(w, 'Item')}
            if name.upper() in names and len(names) <= 3:
                return root
        for _src, root in self.personalities:
            cut = filter_personality(root, name)
            if cut is not None:
                return cut
        return None


def _lists_weapon(el: ET.Element, name: str) -> bool:
    w = el.find('Weapons')
    return w is not None and name.upper() in (text_of(i).upper() for i in elements(w, 'Item'))


def filter_personality(root: ET.Element, name: str) -> ET.Element | None:
    """全武器入りの pedpersonality から、その武器を挙げている項目だけを残した複製。無ければ None。

    - MovementModeUnholsterData: その武器を挙げている UnholsterClips の項目だけを残し、空になった項目は外す
    - MovementModes: 動きの種類ごとの並び(配列)は位置に意味があるので残し、中の候補だけを絞る。
      その武器を1つも挙げていない項目(DEFAULT_ACTION など)は丸ごと外す
    """
    out = ET.Element(root.tag)
    found = False
    unh = root.find('MovementModeUnholsterData')
    if unh is not None:
        dst = ET.SubElement(out, 'MovementModeUnholsterData')
        for u in elements(unh, 'Item'):
            clips = u.find('UnholsterClips')
            keep = [c for c in elements(clips, 'Item') if _lists_weapon(c, name)] if clips is not None else []
            if not keep:
                continue
            u2 = copy.deepcopy(u)
            c2 = u2.find('UnholsterClips')
            for c in list(c2):
                c2.remove(c)
            for c in keep:
                c2.append(copy.deepcopy(c))
            dst.append(u2)
            found = True
    modes = root.find('MovementModes')
    if modes is not None:
        dst = ET.SubElement(out, 'MovementModes')
        for m in elements(modes, 'Item'):
            m2 = copy.deepcopy(m)
            inner = m2.find('MovementModes')
            if inner is None:
                continue
            hit = False
            for arr in elements(inner, 'Item'):
                for v in elements(arr, 'Item'):
                    if _lists_weapon(v, name):
                        hit = True
                    else:
                        arr.remove(v)
            if hit:
                dst.append(m2)
                found = True
    return out if found else None


def choose_donor(w: FoundWeapon, lib: TemplateLibrary) -> str:
    """動作・構え方を借りるテンプレート。見つからなければ空文字。"""
    names = set(lib.weapon_names())
    candidates = []
    if w.name in DONORS:
        candidates.append(DONORS[w.name])
    if w.name.endswith('_MK2'):
        candidates.append(w.name[:-4])
    one, two = GROUP_DONORS.get(w.group, ('', ''))
    candidates.append(two if w.two_handed else one)
    return next((c for c in candidates if c and c in names and c != w.name), '')


def _rename_weapon_lists(root: ET.Element, name: str) -> None:
    for weapons in list(root.iter('Weapons')):
        if not elements(weapons, 'Item'):
            continue
        for child in list(weapons):
            weapons.remove(child)
        ET.SubElement(weapons, 'Item').text = name


def weapon_template(idx: MetaIndex, name: str, lib: TemplateLibrary, donor: str = '') -> tuple[dict[str, ET.Element], dict]:
    """1つの武器のテンプレート(ファイル名 → 要素)と、template.json に書く情報を作る。"""
    w = idx.weapons[name]
    item = copy.deepcopy(w.item)
    attach = w.attach_points()
    ap = item.find('AttachPoints')
    if ap is not None:          # バニラの部品はテンプレートに残さない(付ける部品は利用者が決める)
        for c in list(ap):
            ap.remove(c)
    root = ET.Element('CWeaponInfoBlob')
    slot = text_of(item.find('Slot'))
    if slot:
        nav = ET.SubElement(ET.SubElement(ET.SubElement(root, 'SlotNavigateOrder'), 'Item'), 'WeaponSlots')
        entry = ET.SubElement(nav, 'Item')
        ET.SubElement(entry, 'OrderNumber', {'value': w.order or '300'})
        ET.SubElement(entry, 'Entry').text = slot
    ET.SubElement(ET.SubElement(ET.SubElement(root, 'Infos'), 'Item'), 'Infos').append(item)
    ET.SubElement(root, 'Name').text = 'KN_WTK'
    files: dict[str, ET.Element] = {'weapons.meta': root}
    info: dict = {'source': os.path.basename(w.source), 'attach_points': attach}

    donor_tpl = None
    if donor:
        try:
            donor_tpl = lib.weapon(donor)
        except MetaError:
            donor_tpl = None

    own = idx.own_animations(name)
    if own:
        anim = ET.Element('CWeaponAnimationsSets')
        sets = ET.SubElement(anim, 'WeaponAnimationsSets')
        for aset, it in own:
            s = ET.SubElement(sets, 'Item', {'key': aset.get('key', '')})
            for child in elements(aset):
                if child.tag != 'WeaponAnimations':
                    s.append(copy.deepcopy(child))
            ET.SubElement(s, 'WeaponAnimations').append(copy.deepcopy(it))
        files['weaponanimations.meta'] = anim
        info['animations'] = 'own'
    elif donor_tpl is not None and donor_tpl.animations_root() is not None:
        anim = donor_tpl.animations_root()
        old = (donor_tpl.internal_name or donor_tpl.name).upper()
        for it in anim.iter('Item'):
            if it.get('key', '').upper() == old:
                it.set('key', name)
        files['weaponanimations.meta'] = anim
        info['animations'] = f'borrowed:{donor_tpl.name}'

    pp = idx.own_personality(name)
    if pp is not None:
        pp = copy.deepcopy(pp)
        info['personality'] = 'own'
    elif donor_tpl is not None and donor_tpl.personality_root() is not None:
        pp = donor_tpl.personality_root()
        info['personality'] = f'borrowed:{donor_tpl.name}'
    if pp is not None:
        _rename_weapon_lists(pp, name)
        files['pedpersonality.meta'] = pp
    return files, info


def component_template(idx: MetaIndex, name: str, bones: dict[str, Counter] | None = None) -> ET.Element:
    """1つの部品のテンプレート。WeaponAttachBone(このツールの目印)に、バニラで最も多い取り付けボーンを入れる。"""
    c = idx.components[name]
    item = copy.deepcopy(c.item)
    for old in item.findall('WeaponAttachBone'):
        item.remove(old)
    counts = (bones if bones is not None else idx.bone_counts()).get(name)
    bone = counts.most_common(1)[0][0] if counts else infer_weapon_bone(item)
    if bone:
        wab = ET.Element('WeaponAttachBone')
        wab.text = bone
        # AttachBone の直後に置く(既存テンプレートと同じ並び)
        kids = list(item)
        pos = next((i + 1 for i, k in enumerate(kids) if k.tag == 'AttachBone'), len(kids))
        item.insert(pos, wab)
    root = ET.Element('CWeaponComponentInfoBlob')
    ET.SubElement(root, 'Infos').append(item)
    ET.SubElement(root, 'InfoBlobName')
    return root


def write_template(folder: Path, files: dict[str, ET.Element], info: dict | None = None) -> None:
    """テンプレートのフォルダを丸ごと書く。既存のフォルダは書き終えてから置き換える。"""
    folder = Path(folder)
    folder.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f'.{folder.name}.', suffix='.tmp', dir=folder.parent))
    old: Path | None = None
    try:
        for fn, root in files.items():
            (tmp / fn).write_bytes(dumps(root))
        if info:
            (tmp / TEMPLATE_INFO).write_text(json.dumps(info, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        if folder.exists():
            # 先に消すと、消す途中で失敗したとき(ファイルを開いている等)に前のテンプレートが半分壊れる。
            # 退避 → 置き換え → 退避先を消す、の順にする
            old = Path(tempfile.mkdtemp(prefix=f'.{folder.name}.', suffix='.old', dir=folder.parent))
            os.rmdir(old)
            os.rename(folder, old)
        try:
            os.rename(tmp, folder)
        except OSError:
            if old is not None:
                os.rename(old, folder)
                old = None
            raise
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    if old is not None:
        shutil.rmtree(old, ignore_errors=True)


def import_into(idx: MetaIndex, dest: Path, lib: TemplateLibrary, weapons: list[str], components: list[str]
                ) -> list[tuple[str, str]]:
    """選んだ武器・部品を dest/weapons, dest/components に書く。書けなかったものを (名前, 理由) で返す。"""
    failed: list[tuple[str, str]] = []
    bones = idx.bone_counts()
    # 名前はフォルダ名になる。一覧から選んだ名前(importable_*)以外が来ても dest の外へ書かない
    bad = [n for n in weapons + components if not _NAME_OK.match(n)]
    failed += [(n, 'invalid name') for n in bad]
    weapons = [n for n in weapons if n not in bad]
    components = [n for n in components if n not in bad]
    for name in components:
        try:
            write_template(dest / 'components' / name, {'weaponcomponents.meta': component_template(idx, name, bones)})
        except (OSError, KeyError) as e:
            failed.append((name, str(e)))
    for name in weapons:
        try:
            files, info = weapon_template(idx, name, lib, choose_donor(idx.weapons[name], lib))
            write_template(dest / 'weapons' / name, files, info)
        except (OSError, KeyError, MetaError) as e:
            failed.append((name, str(e)))
    lib.reload()
    return failed


__all__ = ['MetaIndex', 'FoundWeapon', 'FoundComponent', 'choose_donor', 'filter_personality', 'weapon_template', 'component_template',
           'write_template', 'import_into', 'path_priority', 'find_weapon_item']
