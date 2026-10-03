"""テンプレート(バニラ武器の meta 一式)の読み込み。

templates/weapons/<WEAPON_X>/{weapons,weaponanimations,pedpersonality}.meta
templates/components/<COMPONENT_X>/weaponcomponents.meta
一覧はフォルダを走査して作るので、フォルダを足せばそのまま選べる。
"""
from __future__ import annotations

import copy
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .xmlio import MetaError, elements, parse_file, text_of

# テンプレート名はフォルダ名。区切り文字や .. を通さない(templates/ の外を読ませない)
_NAME_RE = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_\-. ]*$')


def _check_name(name: str) -> None:
    if not _NAME_RE.match(name) or '..' in name:
        raise MetaError(f'invalid template name: {name!r}')


TEMPLATE_INFO = 'template.json'     # 出どころ・借りた動作・バニラの取り付けボーンなど(任意)

# 専用の入力欄で決める項目(項目一覧には出さない)
MANAGED_TAGS = ('Name', 'Model', 'Slot', 'HumanNameHash')

# コンポーネント側のボーン名 → 武器側のボーン名。テンプレートに WeaponAttachBone が無いときの補完に使う
_BONE_MAP = {
    'AAPClip': 'WAPClip', 'AAPSupp': 'WAPSupp', 'AAPScop': 'WAPScop', 'AAPFlsh': 'WAPFlshLasr',
    'AAPGrip': 'WAPGrip', 'AAPBarrel': 'WAPBarrel', 'AAPCover': 'WAPFlshLasr',
}
_TYPE_BONES = {
    'CWeaponComponentClipInfo': 'WAPClip', 'CWeaponComponentSuppressorInfo': 'WAPSupp',
    'CWeaponComponentScopeInfo': 'WAPScop', 'CWeaponComponentFlashLightInfo': 'WAPFlshLasr',
}
KNOWN_BONES = ['WAPClip', 'WAPClip_2', 'WAPSupp', 'WAPSupp_2', 'WAPScop', 'WAPScop_2', 'WAPFlshLasr', 'WAPFlsh_2',
               'WAPGrip', 'WAPGrip_2', 'WAPBarrel']


@dataclass(frozen=True)
class Field:
    """CWeaponInfo 直下の、値を1つだけ持つ項目。"""
    tag: str
    kind: str       # 'value'(value 属性) / 'ref'(ref 属性) / 'text'(中身の文字列)
    value: str


def field_of(el: ET.Element) -> Field | None:
    if len(elements(el)):
        return None
    keys = set(el.attrib)
    if keys == {'value'}:
        return Field(el.tag, 'value', el.get('value', ''))
    if keys == {'ref'}:
        return Field(el.tag, 'ref', el.get('ref', ''))
    if not keys:
        return Field(el.tag, 'text', text_of(el))
    return None     # ベクトル(x/y/z)などは対象外


_TAG_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def collect_fields(item: ET.Element) -> list[Field]:
    """編集できる項目。直下の値に加え、一段下の入れ子(<Fx> や <Explosion> の中)も 'Fx/FlashFx' の形で並べる。

    中身が Item の並び(リスト)になっている要素は対象外(個数が武器ごとに違い、値として扱えない)。
    """
    out: list[Field] = []
    for c in elements(item):
        if c.tag in MANAGED_TAGS:
            continue
        f = field_of(c)
        if f is not None:
            out.append(f)
            continue
        kids = elements(c)
        if not kids or any(k.tag == 'Item' for k in kids):
            continue
        for k in kids:
            fk = field_of(k)
            if fk is not None:
                out.append(Field(f'{c.tag}/{k.tag}', fk.kind, fk.value))
    return out


def find_field_element(item: ET.Element, path: str) -> ET.Element | None:
    """'Fx/FlashFx' の形の名前で要素を探す。各段は直下の要素を名前の一致で探す(パス式としては解釈しない)。"""
    parts = path.split('/')
    if not 1 <= len(parts) <= 2 or not all(_TAG_RE.match(p) for p in parts):
        return None
    el = item
    for p in parts:
        el = next((c for c in elements(el) if c.tag == p), None)
        if el is None:
            return None
    return el


def set_field(el: ET.Element, kind: str, value: str) -> None:
    if kind in ('value', 'ref'):
        el.set(kind, value)
    else:
        el.text = value or None


def find_weapon_item(root: ET.Element, prefer: str = '') -> ET.Element | None:
    """CWeaponInfo の要素。位置ではなく type で探す(弾薬定義などが先に並ぶテンプレートがある)。"""
    items = [i for i in root.iter('Item') if i.get('type') == 'CWeaponInfo']
    for i in items:
        if prefer and text_of(i.find('Name')).upper() == prefer.upper():
            return i
    return items[0] if items else None


def bone_family(bone: str) -> str:
    """WAPSupp_2 → WAPSupp。同じ役割のボーンは武器モデルによって _2 / _3 が付く。"""
    return re.sub(r'_\d+$', '', bone)


def infer_weapon_bone(item: ET.Element) -> str:
    """このコンポーネントを付ける武器側のボーン。分からなければ空文字。"""
    explicit = text_of(item.find('WeaponAttachBone'))
    if explicit:
        return explicit
    bone = text_of(item.find('AttachBone'))
    if bone in _BONE_MAP:
        return _BONE_MAP[bone]
    if bone.startswith('AAP') and len(bone) > 3:
        return 'WAP' + bone[3:]
    return _TYPE_BONES.get(item.get('type', ''), '')


@dataclass
class WeaponTemplate:
    name: str
    dir: Path
    _root: ET.Element = field(repr=False)
    model: str = ''
    slot: str = ''
    group: str = ''
    fields: list[Field] = field(default_factory=list)
    attach_points: list[tuple[str, list[str]]] = field(default_factory=list)
    internal_name: str = ''
    source: str = 'bundled'     # 'bundled'(同梱) / 'user'(取り込んだもの)
    info: dict = field(default_factory=dict)        # template.json の中身
    _cache: dict[str, ET.Element | None] = field(default_factory=dict, repr=False)

    def vanilla_attach_points(self) -> list[tuple[str, list[str]]]:
        """バニラのこの武器が使う取り付けボーンと部品(template.json に記録があれば)。"""
        out = []
        for entry in self.info.get('attach_points', []):
            if isinstance(entry, (list, tuple)) and len(entry) == 2 and isinstance(entry[1], list):
                out.append((str(entry[0]), [str(c) for c in entry[1]]))
        return out

    def borrowed(self, kind: str) -> str:
        """動作('animations')・構え方('personality')を借りた武器の名前。借りていなければ空文字。"""
        v = str(self.info.get(kind, ''))
        return v.split(':', 1)[1] if v.startswith('borrowed:') else ''

    def bone_for(self, component: 'ComponentTemplate') -> str:
        """この武器にその部品を付けるボーン。分からなければ空文字。

        1. バニラのこの武器がその部品を付けているボーン
        2. 同じ役割のボーン(WAPSupp と WAPSupp_2 など)をこの武器が使っていれば、それ
        """
        points = self.vanilla_attach_points() + self.attach_points
        for bone, comps in points:
            if component.internal_name.upper() in (c.upper() for c in comps):
                return bone
        family = bone_family(component.weapon_bone)
        used = Counter(bone for bone, comps in points for _ in comps if family and bone_family(bone) == family)
        return used.most_common(1)[0][0] if used else ''

    def weapons_root(self) -> ET.Element:
        return copy.deepcopy(self._root)

    def field(self, tag: str) -> Field | None:
        return next((f for f in self.fields if f.tag == tag), None)

    def _optional_root(self, filename: str) -> ET.Element | None:
        # 点検のたびに読み直さないよう、最初の1回だけ読んで複製を返す(壊れていれば毎回 MetaError)
        if filename not in self._cache:
            p = self.dir / filename
            self._cache[filename] = parse_file(p) if p.is_file() else None
        root = self._cache[filename]
        return copy.deepcopy(root) if root is not None else None

    def animations_root(self) -> ET.Element | None:
        return self._optional_root('weaponanimations.meta')

    def personality_root(self) -> ET.Element | None:
        return self._optional_root('pedpersonality.meta')


@dataclass
class ComponentTemplate:
    name: str
    dir: Path
    _item: ET.Element = field(repr=False)
    internal_name: str = ''
    type: str = ''
    model: str = ''
    weapon_bone: str = ''
    clip_size: int | None = None
    has_ammo_info: bool = False
    ammo_info: str = ''
    source: str = 'bundled'

    @property
    def is_clip(self) -> bool:
        return self.clip_size is not None

    def item(self) -> ET.Element:
        return copy.deepcopy(self._item)


class TemplateLibrary:
    """テンプレートの一覧。roots は優先順(取り込んだもの → 同梱)。同じ名前は先の方を使う。"""

    def __init__(self, root: Path | list[Path]):
        roots = root if isinstance(root, (list, tuple)) else [root]
        self.roots = [Path(r) for r in roots]
        self.root = self.roots[-1]      # 同梱テンプレートの場所
        self._weapons: dict[str, WeaponTemplate] = {}
        self._components: dict[str, ComponentTemplate] = {}
        self._game_models: set[str] | None = None

    def reload(self) -> None:
        self._weapons.clear()
        self._components.clear()
        self._game_models = None

    def game_models(self) -> set[str]:
        """テンプレート武器が使うモデル名(小文字)。ゲームに最初から入っているので、同梱しなくても表示される。"""
        if self._game_models is None:
            models: set[str] = set()
            for n in self.weapon_names():
                try:
                    m = self.weapon(n).model.strip().lower()
                except MetaError:
                    continue
                if m:
                    models.add(m)
            self._game_models = models
        return self._game_models

    def _locate(self, kind: str, name: str, filename: str) -> tuple[Path, str]:
        for i, r in enumerate(self.roots):
            d = r / kind / name
            if (d / filename).is_file():
                return d, ('user' if i < len(self.roots) - 1 else 'bundled')
        return self.root / kind / name, 'bundled'

    def _names(self, kind: str, filename: str) -> list[str]:
        names: set[str] = set()
        for r in self.roots:
            try:
                # . で始まるのは取り込み中・置き換え中の作業フォルダ(.<名前>.tmp / .old)
                names |= {d.name for d in (r / kind).iterdir() if not d.name.startswith('.') and (d / filename).is_file()}
            except OSError:
                pass
        return sorted(names, key=str.upper)

    def weapon_names(self) -> list[str]:
        return self._names('weapons', 'weapons.meta')

    def component_names(self) -> list[str]:
        return self._names('components', 'weaponcomponents.meta')

    def weapon(self, name: str) -> WeaponTemplate:
        """読めない・武器定義が無いときは MetaError。"""
        if name in self._weapons:
            return self._weapons[name]
        _check_name(name)
        d, source = self._locate('weapons', name, 'weapons.meta')
        root = parse_file(d / 'weapons.meta')
        item = find_weapon_item(root, name)
        if item is None:
            raise MetaError(f'{d / "weapons.meta"}: no CWeaponInfo item')
        t = WeaponTemplate(name=name, dir=d, _root=root, source=source)
        try:
            info = json.loads((d / TEMPLATE_INFO).read_text(encoding='utf-8'))
            t.info = info if isinstance(info, dict) else {}
        except (OSError, ValueError):
            t.info = {}     # 無い・壊れているときは記録なしとして扱う
        t.internal_name = text_of(item.find('Name'))
        t.model = text_of(item.find('Model'))
        t.slot = text_of(item.find('Slot'))
        t.group = text_of(item.find('Group'))
        t.fields = collect_fields(item)
        ap = item.find('AttachPoints')
        if ap is not None:
            for p in elements(ap, 'Item'):
                names = [text_of(c.find('Name')) for c in p.findall('Components/Item')]
                t.attach_points.append((text_of(p.find('AttachBone')), names))
        self._weapons[name] = t
        return t

    def component(self, name: str) -> ComponentTemplate:
        if name in self._components:
            return self._components[name]
        _check_name(name)
        d, source = self._locate('components', name, 'weaponcomponents.meta')
        root = parse_file(d / 'weaponcomponents.meta')
        item = root.find('Infos/Item')
        if item is None:
            raise MetaError(f'{d / "weaponcomponents.meta"}: no Infos/Item')
        t = ComponentTemplate(name=name, dir=d, _item=item, source=source)
        t.internal_name = text_of(item.find('Name')) or name
        t.type = item.get('type', '')
        t.model = text_of(item.find('Model'))
        t.weapon_bone = infer_weapon_bone(item)
        clip = item.find('ClipSize')
        if clip is not None:
            try:
                t.clip_size = int(float(clip.get('value', '0')))
            except (ValueError, OverflowError):     # "abc" / "inf" / "nan" など
                t.clip_size = 0
        ammo = item.find('AmmoInfo')
        t.has_ammo_info = ammo is not None
        t.ammo_info = text_of(ammo)
        self._components[name] = t
        return t

    def scan_problems(self) -> list[tuple[str, str]]:
        """全テンプレートを読んでみて、壊れているものを (名前, 理由) で返す。"""
        out: list[tuple[str, str]] = []
        for n in self.weapon_names():
            try:
                t = self.weapon(n)
                t.animations_root()
                t.personality_root()
            except MetaError as e:
                out.append((n, str(e)))
        for n in self.component_names():
            try:
                self.component(n)
            except MetaError as e:
                out.append((n, str(e)))
        return out
