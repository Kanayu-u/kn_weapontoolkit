"""ファイル名からの推測(武器モデル・コンポーネント)。あくまで候補で、利用者が直せる。"""
from __future__ import annotations

import re

from .assets import Asset
from .model import ComponentSpec, Project
from .templates import TemplateLibrary
from .xmlio import MetaError

_PISTOL_GROUPS = ('GROUP_PISTOL',)

# (接尾辞の正規表現, 種類)
_KINDS = [
    (re.compile(r'^(?:mag|clip)_?0?(\d)$'), 'clip'),
    (re.compile(r'^(?:box)?mag$'), 'clip'),
    (re.compile(r'^supp(?:ressor)?(?:_?0?\d)?$'), 'supp'),
    (re.compile(r'^scope(?:_?\w+)?$'), 'scope'),
    (re.compile(r'^(?:af)?grip(?:_?0?\d)?$'), 'grip'),
    (re.compile(r'^(?:flsh|flash|flashlight|light)(?:_?0?\d)?$'), 'flsh'),
]


def base_models(assets: list[Asset]) -> list[str]:
    """本体モデル(_hi でない .ydr)の名前。元の大文字小文字のまま。"""
    return [a.name[:-4] for a in assets if a.is_base_model]


def guess_weapon_model(assets: list[Asset]) -> str:
    """武器本体らしいモデル名。部品(名前_mag1 など)をいちばん多く従えているもの。決められなければ空文字。"""
    names = sorted({n.lower() for n in base_models(assets)}, key=lambda n: (len(n), n))
    if len(names) == 1:
        return names[0]
    children = {n: sum(1 for o in names if o.startswith(n + '_')) for n in names}
    best = max(children.values(), default=0)
    if best > 0:
        return next(n for n in names if children[n] == best)
    # 部品が無いときは、手持ち用モデル(_hi)を持つものが1つだけならそれ
    keys = {a.key for a in assets}
    with_hi = [n for n in names if f'{n}_hi.ydr' in keys]
    return with_hi[0] if len(with_hi) == 1 else ''


_CLIP_RE = re.compile(r'^COMPONENT_.+?_((?:CLIP|MAG)_?\d+|BOXMAG)$')


def auto_component_name(weapon_id: str, template: str, taken: set[str] = frozenset()) -> str:
    """テンプレート名から、この武器用のコンポーネント名を作る。taken(大文字)と重ならないよう番号を足す。"""
    ident = weapon_id.upper().removeprefix('WEAPON_') or 'CUSTOM'
    m = _CLIP_RE.match(template)
    if m:
        tail = m.group(1)
    else:
        tail = template.removeprefix('COMPONENT_').removeprefix('AT_')
    base = name = f'COMPONENT_{ident}_{tail}'
    i = 2
    while name.upper() in taken:
        name = f'{base}_{i}'
        i += 1
    return name


def _first_existing(lib: TemplateLibrary, candidates: list[str]) -> str:
    names = set(lib.component_names())
    return next((c for c in candidates if c in names), '')


def suggest_components(project: Project, lib: TemplateLibrary, assets: list[Asset]) -> list[ComponentSpec]:
    """武器モデル名で始まる部品モデル(w_x_mag1 など)からコンポーネントの候補を作る。既にあるモデルは除く。"""
    model = project.model.strip().lower()
    if not model:
        return []
    try:
        group = lib.weapon(project.template).group
    except MetaError:
        group = ''
    pistol = group in _PISTOL_GROUPS
    short = project.template.removeprefix('WEAPON_')
    ident = project.weapon_id.upper().removeprefix('WEAPON_') or 'CUSTOM'
    have_models = {c.model.strip().lower() for c in project.components}
    have_names = {c.name.upper() for c in project.components}
    out: list[ComponentSpec] = []
    clip_default_taken = any(c.default and c.clip_size is not None for c in project.components)

    for name in sorted(base_models(assets), key=str.lower):
        low = name.lower()
        if not low.startswith(model + '_') or low in have_models:
            continue
        suffix = low[len(model) + 1:]
        kind, num = '', ''
        for rx, k in _KINDS:
            m = rx.match(suffix)
            if m:
                kind, num = k, (m.group(1) if m.groups() else '')
                break
        if kind == 'clip':
            n = num or '1'
            tpl = _first_existing(lib, [f'COMPONENT_{short}_CLIP_0{n}', f'COMPONENT_{short}_CLIP_01',
                                        'COMPONENT_PISTOL_CLIP_01' if pistol else 'COMPONENT_CARBINERIFLE_CLIP_01'])
            cname = f'COMPONENT_{ident}_CLIP_0{n}'
        elif kind == 'supp':
            tpl = _first_existing(lib, ['COMPONENT_AT_PI_SUPP' if pistol else 'COMPONENT_AT_AR_SUPP'])
            cname = f'COMPONENT_{ident}_SUPP'
        elif kind == 'scope':
            tpl = _first_existing(lib, ['COMPONENT_AT_SCOPE_MACRO' if pistol else 'COMPONENT_AT_SCOPE_MEDIUM'])
            cname = f'COMPONENT_{ident}_SCOPE'
        elif kind == 'grip':
            tpl = _first_existing(lib, ['COMPONENT_AT_AR_AFGRIP'])
            cname = f'COMPONENT_{ident}_GRIP'
        elif kind == 'flsh':
            tpl = _first_existing(lib, ['COMPONENT_AT_PI_FLSH' if pistol else 'COMPONENT_AT_AR_FLSH'])
            cname = f'COMPONENT_{ident}_FLSH'
        else:
            continue
        if not tpl:
            continue
        base, i = cname, 2
        while cname.upper() in have_names:
            cname = f'{base}_{i}'
            i += 1
        have_names.add(cname.upper())
        try:
            ct = lib.component(tpl)
        except MetaError:
            continue
        spec = ComponentSpec(template=tpl, name=cname, model=low, clip_size=ct.clip_size)
        if ct.is_clip and not clip_default_taken:
            spec.default = True         # 最初のクリップだけ装着済みにする
            clip_default_taken = True
        out.append(spec)
    return out
