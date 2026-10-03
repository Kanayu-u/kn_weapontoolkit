"""プロジェクトから FiveM リソース一式を作る。

build() はファイルの中身を作るだけ(ディスクに触らない)。export() は一時フォルダに全部書いてから
目的の場所へ移すので、途中で失敗しても中途半端なリソースは残らない。
"""
from __future__ import annotations

import math
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from . import APP_DISPLAY_NAME, __version__
from .assets import Asset
from .model import ComponentSpec, Project
from .templates import (ComponentTemplate, TemplateLibrary, WeaponTemplate, field_of, find_field_element,
                        find_weapon_item, set_field)
from .xmlio import MetaError, dumps, elements, set_child_text, text_of

# 読み込み順は fxmanifest の data_file の順。部品 → モデル定義 → 動作 → 武器本体
META_FILES = [
    ('WEAPONCOMPONENTSINFO_FILE', 'weaponcomponents.meta'),
    ('WEAPON_METADATA_FILE', 'weaponarchetypes.meta'),
    ('WEAPON_ANIMATIONS_FILE', 'weaponanimations.meta'),
    ('PED_PERSONALITY_FILE', 'pedpersonality.meta'),
    ('WEAPONINFO_FILE', 'weapons.meta'),
]
_RESOURCE_NAME_RE = re.compile(r'^[A-Za-z0-9_\-]+$')
MANIFEST = 'fxmanifest.lua'
NAMES_SCRIPT = 'cl_weaponNames.lua'


class ExportError(Exception):
    """書き出せない。args[0] は利用者向けの文。"""


@dataclass
class BuildResult:
    files: dict[str, bytes] = field(default_factory=dict)       # リソース内の相対パス(/ 区切り) → 中身
    assets: list[Asset] = field(default_factory=list)           # stream/ へコピーするファイル
    skipped_fields: list[str] = field(default_factory=list)     # テンプレートに無くて書けなかった項目


def component_bone(spec: ComponentSpec, tpl: ComponentTemplate, weapon: WeaponTemplate | None = None) -> str:
    """部品を付けるボーン。手動指定 → テンプレート武器のバニラ定義 → 部品テンプレートの順に決める。"""
    if spec.bone.strip():
        return spec.bone.strip()
    if weapon is not None:
        bone = weapon.bone_for(tpl)
        if bone:
            return bone
    return tpl.weapon_bone


def included_assets(project: Project, assets: list[Asset]) -> list[Asset]:
    excluded = set(project.excluded_assets)
    return [a for a in assets if a.key not in excluded]


def _fmt_float(v: float) -> str:
    return f'{v:.6f}'


def _lua_str(s: str) -> str:
    out = s.replace('\\', '\\\\').replace("'", "\\'").replace('\r', '').replace('\n', '\\n')
    return f"'{out}'"


def build_weapons_meta(project: Project, lib: TemplateLibrary, skipped: list[str]) -> ET.Element:
    tpl = lib.weapon(project.template)
    root = tpl.weapons_root()
    item = find_weapon_item(root, project.template)
    old_slot = text_of(item.find('Slot'))
    new_slot = project.slot_name()

    set_child_text(item, 'Name', project.weapon_id)
    set_child_text(item, 'Model', project.model.strip())
    set_child_text(item, 'Slot', new_slot)
    set_child_text(item, 'HumanNameHash', project.weapon_id)    # 表示名は cl_weaponNames.lua の AddTextEntry で与える

    # 武器ホイールの並び: テンプレートのスロット名を指している箇所だけ書き換える
    for section in ('SlotNavigateOrder', 'SlotBestOrder'):
        sec = root.find(section)
        if sec is None:
            continue
        for slot in sec.iter('Item'):
            entry = slot.find('Entry')
            if entry is None or (old_slot and text_of(entry) != old_slot):
                continue
            entry.text = new_slot
            order = slot.find('OrderNumber')
            if section == 'SlotNavigateOrder' and order is not None and project.slot_order is not None:
                order.set('value', str(project.slot_order))

    for tag, value in project.fields.items():
        # find() はタグ名をパス式として解釈する("[" などを渡せてしまう)ので、名前の一致で一段ずつ探す。
        # 編集できる項目(tpl.fields)に無いもの(Name など専用の欄で決める項目)は、手で書き換えたプロジェクトでも書かない
        el = find_field_element(item, tag) if tpl.field(tag) is not None else None
        f = field_of(el) if el is not None else None
        if f is None:
            skipped.append(tag)     # 無い項目は作らない(テンプレートに無い構造を捏造しない)
            continue
        set_field(el, f.kind, value)

    _apply_attach_points(project, lib, item)
    return root


def _apply_attach_points(project: Project, lib: TemplateLibrary, item: ET.Element) -> None:
    ap = item.find('AttachPoints')
    if ap is None:
        if not project.components:
            return
        ap = ET.SubElement(item, 'AttachPoints')
    if not project.keep_template_attachments:
        for child in list(ap):
            ap.remove(child)

    weapon = lib.weapon(project.template)
    by_bone: dict[str, list[ComponentSpec]] = {}
    for c in project.components:
        bone = component_bone(c, lib.component(c.template), weapon)
        if not bone:
            raise ExportError(f'{c.name}: attach bone is unknown')
        by_bone.setdefault(bone, []).append(c)

    for bone, comps in by_bone.items():
        # 同じボーンにテンプレート由来の定義があれば置き換える(同じボーンの Item を2つ作らない)
        point = next((p for p in elements(ap, 'Item') if text_of(p.find('AttachBone')) == bone), None)
        if point is None:
            point = ET.SubElement(ap, 'Item')
            ET.SubElement(point, 'AttachBone').text = bone
        for old in point.findall('Components'):
            point.remove(old)
        clist = ET.SubElement(point, 'Components')
        for c in comps:
            ci = ET.SubElement(clist, 'Item')
            ET.SubElement(ci, 'Name').text = c.name
            ET.SubElement(ci, 'Default', {'value': 'true' if c.default else 'false'})


def build_components_meta(project: Project, lib: TemplateLibrary) -> ET.Element:
    root = ET.Element('CWeaponComponentInfoBlob')
    infos = ET.SubElement(root, 'Infos')
    for c in project.components:
        tpl = lib.component(c.template)
        item = tpl.item()
        set_child_text(item, 'Name', c.name)
        model = item.find('Model')
        if model is not None:
            model.text = c.model or None
        elif c.model:
            raise ExportError(f'{c.name}: template {c.template} has no <Model>')
        # WeaponAttachBone はこのツールがテンプレートに持たせている目印で、ゲームの定義には無い
        for extra in item.findall('WeaponAttachBone'):
            item.remove(extra)
        clip = item.find('ClipSize')
        if clip is not None and c.clip_size is not None:
            clip.set('value', str(c.clip_size))
        ammo = item.find('AmmoInfo')
        if ammo is not None:
            ammo.text = c.ammo_info or None
        infos.append(item)
    ET.SubElement(root, 'InfoBlobName').text = project.effective_resource_name()
    return root


def build_animations_meta(project: Project, lib: TemplateLibrary) -> ET.Element | None:
    tpl = lib.weapon(project.template)
    root = tpl.animations_root()
    if root is None:
        return None
    old = tpl.internal_name or tpl.name
    for aset in root.findall('WeaponAnimationsSets/Item'):
        items = aset.findall('WeaponAnimations/Item')
        targets = [i for i in items if i.get('key', '').upper() == old.upper()]
        if not targets and items and items[0].get('key', '').upper().startswith('WEAPON_'):
            targets = [items[0]]    # 別武器の動作を借りているテンプレート(元ツールと同じく先頭を使う)
        for i in targets:
            i.set('key', project.weapon_id)
            if project.fire_rate is None:
                continue
            if not math.isfinite(project.fire_rate) or project.fire_rate <= 0:
                raise ExportError(f'invalid fire rate: {project.fire_rate}')
            rate = i.find('AnimFireRateModifier')
            if rate is None:
                rate = ET.SubElement(i, 'AnimFireRateModifier')
            rate.set('value', _fmt_float(project.fire_rate))
    return root


def build_personality_meta(project: Project, lib: TemplateLibrary) -> ET.Element | None:
    root = lib.weapon(project.template).personality_root()
    if root is None:
        return None
    # どの Weapons リストも新しい武器だけを指すようにする(バニラ武器の定義を巻き添えで上書きしない)
    for weapons in list(root.iter('Weapons')):
        if not elements(weapons, 'Item'):
            continue
        for child in list(weapons):
            weapons.remove(child)
        ET.SubElement(weapons, 'Item').text = project.weapon_id
    return root


def build_archetypes_meta(project: Project, lib: TemplateLibrary, assets: list[Asset]) -> ET.Element:
    root = ET.Element('CWeaponModelInfo__InitDataList')
    datas = ET.SubElement(root, 'InitDatas')
    textures = {a.base for a in assets if a.ext == '.ytd'}
    weapon_model = project.model.strip().lower()
    lods = {c.model.strip().lower(): c.lod for c in project.components if c.model.strip()}
    for a in assets:
        if not a.is_base_model:
            continue
        name = os.path.splitext(a.name)[0]
        key = a.base
        # テクスチャ辞書: 同名の .ytd があればそれ。無ければ武器本体の .ytd を共有しているとみなす
        txd = name if key in textures else (project.model.strip() if weapon_model in textures else name)
        item = ET.SubElement(datas, 'Item')
        ET.SubElement(item, 'modelName').text = name
        ET.SubElement(item, 'txdName').text = txd
        ET.SubElement(item, 'ptfxAssetName').text = 'NULL'
        lod = project.lod if key == weapon_model else lods.get(key, project.lod)
        ET.SubElement(item, 'lodDist', {'value': str(lod)})
    return root


def build_manifest(project: Project, metas: list[str]) -> str:
    lines = [
        "fx_version 'cerulean'",
        "game 'gta5'",
        '',
        f"description {_lua_str(f'Add-on weapon {project.weapon_id} (generated with {APP_DISPLAY_NAME} {__version__})')}",
        '',
        'files {',
    ]
    lines += [f"    'meta/{m}'," for m in metas]
    lines += ['}', '']
    lines += [f"data_file '{kind}' 'meta/{name}'" for kind, name in META_FILES if name in metas]
    lines += ['', f"client_script '{NAMES_SCRIPT}'", '']
    return '\n'.join(lines)


def build_names_script(project: Project) -> str:
    return f'AddTextEntry({_lua_str(project.weapon_id)}, {_lua_str(project.display_name)})\n'


def build(project: Project, lib: TemplateLibrary, assets: list[Asset]) -> BuildResult:
    """リソースの中身を作る。テンプレートが読めなければ MetaError、作れなければ ExportError。"""
    res = BuildResult()
    res.assets = included_assets(project, assets)
    docs: dict[str, ET.Element | None] = {
        'weapons.meta': build_weapons_meta(project, lib, res.skipped_fields),
        'weaponarchetypes.meta': build_archetypes_meta(project, lib, res.assets),
        'weaponanimations.meta': build_animations_meta(project, lib),
        'pedpersonality.meta': build_personality_meta(project, lib),
        'weaponcomponents.meta': build_components_meta(project, lib) if project.components else None,
    }
    metas = [name for _kind, name in META_FILES if docs.get(name) is not None]
    for name in metas:
        res.files[f'meta/{name}'] = dumps(docs[name])
    res.files[MANIFEST] = build_manifest(project, metas).encode('utf-8')
    res.files[NAMES_SCRIPT] = build_names_script(project).encode('utf-8')
    return res


def looks_like_resource(path: Path) -> bool:
    return (path / MANIFEST).is_file()


def stale_dirs(out_dir: str | Path, name: str) -> list[Path]:
    """以前の書き出しが残した作業フォルダ(.<名前>.xxxx.tmp / .old)。消し残りがあれば利用者に知らせる。"""
    try:
        return sorted(p for p in Path(out_dir).iterdir()
                      if p.is_dir() and p.name.startswith(f'.{name}.') and p.suffix in ('.tmp', '.old'))
    except OSError:
        return []


def export(project: Project, lib: TemplateLibrary, assets: list[Asset], out_dir: str | Path,
           overwrite: bool = False) -> Path:
    """out_dir/<リソース名>/ に書き出して、そのパスを返す。詳細は export_build()。"""
    return export_build(project, lib, assets, out_dir, overwrite)[0]


def export_build(project: Project, lib: TemplateLibrary, assets: list[Asset], out_dir: str | Path,
                 overwrite: bool = False) -> tuple[Path, BuildResult]:
    """out_dir/<リソース名>/ に書き出して、(そのパス, 書いた内容) を返す。

    既に同名フォルダがあるとき: overwrite=False なら FileExistsError。True でも、fxmanifest.lua の無い
    フォルダ(リソースではない何か)は消さずに ExportError にする。
    """
    name = project.effective_resource_name()
    if not _RESOURCE_NAME_RE.match(name):
        # フォルダ名として使うので、区切り文字や .. を含む名前は受け付けない(書き出し先の外へ出さない)
        raise ExportError(f'invalid resource name: {name!r}')
    out_dir = Path(out_dir)
    if not out_dir.is_dir():
        raise ExportError(f'output folder not found: {out_dir}')
    target = out_dir / name
    if target.exists():
        if not overwrite:
            raise FileExistsError(str(target))
        if not target.is_dir() or not looks_like_resource(target):
            raise ExportError(f'not a resource folder, refusing to replace: {target}')

    res = build(project, lib, assets)
    try:
        tmp = Path(tempfile.mkdtemp(prefix=f'.{name}.', suffix='.tmp', dir=out_dir))
    except OSError as e:
        raise ExportError(f'{out_dir}: {e.strerror or e}') from e
    old: Path | None = None
    try:
        for rel, data in res.files.items():
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        if res.assets:
            stream = tmp / 'stream'
            stream.mkdir()
            for a in res.assets:
                shutil.copyfile(a.path, stream / a.name)
        if target.exists():
            old = Path(tempfile.mkdtemp(prefix=f'.{name}.', suffix='.old', dir=out_dir))
            os.rmdir(old)
            os.rename(target, old)
        try:
            os.rename(tmp, target)
        except OSError:
            if old is not None:     # 置き換えに失敗したら元へ戻す
                try:
                    os.rename(old, target)
                except OSError as e2:
                    # 元へも戻せなかった。前回の書き出しは退避先に残っているので、場所を伝える
                    shutil.rmtree(tmp, ignore_errors=True)
                    raise ExportError(f'{target}: {e2.strerror or e2} (previous export kept at {old})') from e2
                old = None
            raise
    except OSError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ExportError(f'{e.filename or target}: {e.strerror or e}') from e
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    if old is not None:
        shutil.rmtree(old, ignore_errors=True)
    return target, res


__all__ = ['BuildResult', 'ExportError', 'MetaError', 'build', 'export', 'export_build', 'component_bone',
           'included_assets', 'looks_like_resource', 'stale_dirs']
