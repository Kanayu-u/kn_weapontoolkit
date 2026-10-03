"""編集中の武器1本ぶんの設定。JSON で保存・読込する。"""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

PROJECT_SUFFIX = '.kwtk.json'
FORMAT_VERSION = 1

_ID_RE = re.compile(r'[^A-Za-z0-9_]')


class ProjectError(Exception):
    """プロジェクトファイルが読めない・書けない。"""


@dataclass
class ComponentSpec:
    template: str = ''
    name: str = ''
    model: str = ''
    lod: int = 300
    clip_size: int | None = None    # None = クリップではない / テンプレートのまま
    ammo_info: str = ''             # '' = 武器の弾薬のまま
    default: bool = False           # 最初から付いた状態にする
    bone: str = ''                  # '' = テンプレートから自動

    @classmethod
    def from_dict(cls, d: dict) -> 'ComponentSpec':
        return _from_dict(cls, d)


@dataclass
class Project:
    template: str = 'WEAPON_ASSAULTRIFLE'
    weapon_id: str = 'WEAPON_AK47'
    display_name: str = 'AK-47'
    model: str = 'w_ar_assaultrifle'
    resource_name: str = ''         # '' = 武器 ID を小文字にしたもの
    import_dir: str = ''
    lod: int = 500
    fire_rate: float | None = None  # weaponanimations の AnimFireRateModifier。None = テンプレートのまま
    slot_order: int | None = None   # 武器ホイールの並び順。None = 書き出し時に採番
    keep_template_attachments: bool = True
    fields: dict[str, str] = field(default_factory=dict)        # テンプレートから変えた項目だけ {タグ: 値}
    components: list[ComponentSpec] = field(default_factory=list)
    excluded_assets: list[str] = field(default_factory=list)    # 書き出しに含めないファイル名(小文字)

    def effective_resource_name(self) -> str:
        return self.resource_name.strip() or sanitize_resource_name(self.weapon_id)

    def slot_name(self) -> str:
        return 'SLOT_' + self.weapon_id

    def to_dict(self) -> dict:
        d = asdict(self)
        d['format'] = FORMAT_VERSION
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'Project':
        if not isinstance(d, dict):
            raise ProjectError('not a project file')
        p = _from_dict(cls, {k: v for k, v in d.items() if k != 'components'})
        comps = d.get('components', [])
        p.components = [ComponentSpec.from_dict(c) for c in comps if isinstance(c, dict)] if isinstance(comps, list) else []
        if not isinstance(p.fields, dict):
            p.fields = {}
        p.fields = {str(k): str(v) for k, v in p.fields.items()}
        if not isinstance(p.excluded_assets, list):
            p.excluded_assets = []
        p.excluded_assets = [str(x).lower() for x in p.excluded_assets]
        return p

    def save(self, path: Path) -> None:
        text = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        path = Path(path)
        try:
            # 途中で落ちても元のファイルを壊さないよう、一時ファイルへ書いてから置き換える
            fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(text + '\n')
                os.replace(tmp, path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except OSError as e:
            raise ProjectError(f'{path}: {e.strerror or e}') from e

    @classmethod
    def load(cls, path: Path) -> 'Project':
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        except OSError as e:
            raise ProjectError(f'{path}: {e.strerror or e}') from e
        except ValueError as e:
            raise ProjectError(f'{path}: {e}') from e
        return cls.from_dict(data)


def _from_dict(cls, d: dict):
    """既知のキーだけ、型が合うものだけ取り込む(壊れた値は既定値のまま)。"""
    obj = cls()
    for f in fields(cls):
        if f.name not in d:
            continue
        v = d[f.name]
        cur = getattr(obj, f.name)
        optional = 'None' in str(f.type)
        if v is None:
            if optional:
                setattr(obj, f.name, None)
            continue
        base = str(f.type).split('|')[0].strip()
        if base == 'int':
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            v = int(v)
        elif base == 'float':
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            v = float(v)
        elif base == 'bool':
            if not isinstance(v, bool):
                continue
        elif base == 'str':
            if not isinstance(v, str):
                continue
        elif cur is not None and not isinstance(v, type(cur)):
            continue
        setattr(obj, f.name, v)
    return obj


def sanitize_resource_name(text: str) -> str:
    return _ID_RE.sub('_', text.strip()).strip('_').lower()
