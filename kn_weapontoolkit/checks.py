"""書き出し前の点検。問題を (重さ, 文) の一覧で返す。error が1つでもあれば書き出さない。"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .assets import ScanResult
from .exporter import component_bone, included_assets
from .gamedata import AMMO_TYPES, PROJECTILE_AMMO, VOLUMETRIC_AMMO
from .i18n import tr
from .model import Project
from .templates import TemplateLibrary
from .xmlio import MetaError

ERROR, WARNING, INFO = 'error', 'warning', 'info'
_ID_RE = re.compile(r'^[A-Za-z0-9_]+$')
_RES_RE = re.compile(r'^[A-Za-z0-9_\-]+$')
_MODEL_RE = re.compile(r'^[A-Za-z0-9_\-+.@]+$')


@dataclass(frozen=True)
class Issue:
    level: str
    message: str


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == ERROR for i in issues)


def _is_number(s: str) -> bool:
    if '_' in s:
        return False        # Python の float() は 1_000 を通すが、ゲームの meta では数値として読めない
    try:
        return math.isfinite(float(s))      # nan / inf は数値として書き出さない
    except ValueError:
        return False


def run(project: Project, lib: TemplateLibrary, scan: ScanResult) -> list[Issue]:
    out: list[Issue] = []

    def add(level: str, text: str, /, **kw) -> None:
        out.append(Issue(level, tr(text, **kw)))

    # --- テンプレート
    tpl = None
    try:
        tpl = lib.weapon(project.template)
        if tpl.animations_root() is None:
            add(WARNING, 'テンプレート {name} に weaponanimations.meta がありません。動作の定義なしで書き出します。',
                name=project.template)
        if tpl.personality_root() is None:
            add(WARNING, 'テンプレート {name} に pedpersonality.meta がありません。構え方の定義なしで書き出します。',
                name=project.template)
    except MetaError as e:
        add(ERROR, 'テンプレート {name} を読めません: {reason}', name=project.template, reason=str(e))

    # --- 武器の基本項目
    wid = project.weapon_id
    if not wid:
        add(ERROR, '武器 ID が空です。')
    elif not _ID_RE.match(wid):
        add(ERROR, '武器 ID に使えない文字があります(半角英数字と _ のみ): {id}', id=wid)
    else:
        if not wid.upper().startswith('WEAPON_'):
            add(WARNING, '武器 ID は WEAPON_ で始めるのが通例です: {id}', id=wid)
        if wid != wid.upper():
            add(WARNING, '武器 ID に小文字が含まれています。大文字にそろえるのが通例です: {id}', id=wid)
        if wid.upper() in {n.upper() for n in lib.weapon_names()}:
            add(WARNING, '武器 ID {id} はバニラ武器と同じ名前です。バニラ武器の定義を上書きします。', id=wid)
    if not project.display_name.strip():
        add(ERROR, '表示名が空です。')
    res = project.effective_resource_name()
    if not res:
        add(ERROR, 'リソース名が空です。')
    elif not _RES_RE.match(res):
        add(ERROR, 'リソース名に使えない文字があります(半角英数字と _ - のみ): {name}', name=res)
    if project.lod <= 0:
        add(ERROR, 'LOD 距離は 1 以上にしてください。')
    if project.fire_rate is not None and not (math.isfinite(project.fire_rate) and project.fire_rate > 0):
        add(ERROR, '射撃動作の速度倍率は 0 より大きくしてください。')
    if project.slot_order is not None and project.slot_order < 1:
        add(ERROR, '武器ホイールの並び順は 1 以上にしてください。')

    # --- 項目の上書き
    if tpl is not None:
        for tag, value in project.fields.items():
            f = tpl.field(tag)
            if f is None:
                add(WARNING, '項目 {tag} はテンプレート {name} に無いため書き出されません。', tag=tag, name=project.template)
            elif f.kind == 'value' and not _is_number(value) and value.lower() not in ('true', 'false'):
                add(ERROR, '項目 {tag} の値が数値ではありません: {value}', tag=tag, value=value)
            elif f.kind == 'ref' and not value.strip():
                add(ERROR, '項目 {tag} が空です。', tag=tag)

    # --- 発射方式と弾薬の組み合わせ(バニラに無い組み合わせは、意図どおり動かないことがある)
    if tpl is not None:
        def value(tag: str) -> str:
            f = tpl.field(tag)
            return project.fields.get(tag, f.value if f else '').strip()
        fire, ammo = value('FireType').upper(), value('AmmoInfo').upper()
        if fire == 'PROJECTILE' and ammo and ammo not in PROJECTILE_AMMO and ammo not in VOLUMETRIC_AMMO \
                and ammo in AMMO_TYPES:
            add(WARNING, '発射方式が PROJECTILE ですが、弾薬 {ammo} は飛んでいく弾ではありません。ロケット等を撃たせるなら AMMO_RPG などを選んでください。', ammo=ammo)
        elif fire in ('INSTANT_HIT', 'DELAYED_HIT') and ammo in PROJECTILE_AMMO:
            add(WARNING, '弾薬 {ammo} はバニラでは PROJECTILE(弾が飛ぶ)の武器が使う弾です。発射方式が {fire} のままだと撃ち出されない可能性があります。撃ち出すなら発射方式を PROJECTILE にしてください。', ammo=ammo, fire=fire)
        if (fire == 'VOLUMETRIC_PARTICLE') != (ammo in VOLUMETRIC_AMMO) and fire and ammo:
            add(WARNING, '発射方式 VOLUMETRIC_PARTICLE(噴射)と噴射用の弾薬(AMMO_FIREEXTINGUISHER など)は組み合わせて使います。今は {fire} と {ammo} です。', fire=fire, ammo=ammo)
        # 実機: カービンのモデルから AMMO_RPG を撃つとロケット弾が横向きで飛んだ(RPG のフラグを足しても同じ)
        base_fire = tpl.field('FireType')
        if fire == 'PROJECTILE' and ammo in PROJECTILE_AMMO and base_fire is not None \
                and base_fire.value.strip().upper() != 'PROJECTILE':
            add(WARNING, '弾が飛ぶ武器ではないテンプレートから {ammo} を撃つと、弾が横向きのまま飛ぶことがあります(バニラのカービンのモデルで確認)。弾の向きはモデル側で決まるとみられ、ここの設定では直せません。', ammo=ammo)
        # 実機: Explosion を設定しても DamageType が BULLET のままだと爆発しなかった
        explosion = value('Explosion/Default').upper()
        if explosion and explosion != 'DONTCARE' and value('DamageType').upper() != 'EXPLOSIVE':
            add(WARNING, '着弾時の爆発 {explosion} を使うには、ダメージの種類を EXPLOSIVE にしてください(今は {damage})。そのままでは爆発しません。',
                explosion=explosion, damage=value('DamageType') or '-')
        # 実機: カービンの射撃間隔を 0.135→0.4 にしても連射の速さは変わらず(約127ms)、射撃動作の速度倍率 0.5 で約260ms。
        # ピストル(単発)も 0.1 / 0.37 / 0.8 で連打の最短間隔は約330ms のまま
        base_tbs = tpl.field('TimeBetweenShots')
        if 'TimeBetweenShots' in project.fields and base_tbs is not None \
                and project.fields['TimeBetweenShots'].strip() != base_tbs.value.strip():
            add(WARNING, '射撃間隔を変えても、連射の速さは変わらないことがあります(バニラのカービンとピストルで確認)。連射の速さを変えるには「射撃動作の速度倍率」を使ってください。')

    # --- モデル
    assets = included_assets(project, scan.assets)
    by_key = {a.key: a for a in assets}
    model = project.model.strip().lower()
    # バニラ武器のモデルはゲームに入っているので、ファイルを同梱しなくても表示される
    game_model = bool(model) and f'{model}.ydr' not in by_key and model in lib.game_models()
    if game_model:
        add(WARNING, 'ゲームに入っているモデル {model} を使います(モデルのファイルは同梱しません)。', model=model)
    elif not project.import_dir:
        add(ERROR, 'モデルのフォルダが選ばれていません。')
    elif not scan.assets:
        add(ERROR, 'フォルダにモデル(.ydr)やテクスチャ(.ytd)が見つかりません: {dir}', dir=project.import_dir)
    if not model:
        add(ERROR, '武器モデル名が空です。')
    elif not _MODEL_RE.match(model):
        add(ERROR, '武器モデル名に使えない文字があります: {model}', model=project.model)
    elif f'{model}.ydr' in by_key:
        if f'{model}.ytd' not in by_key:
            add(INFO, '{model}.ytd がありません。テクスチャがモデルに埋め込まれていれば問題ありません。', model=model)
        if f'{model}_hi.ydr' not in by_key:
            add(INFO, '{model}_hi.ydr がありません。手に持ったときも通常モデルが使われます。', model=model)
        if model in lib.game_models():
            add(INFO, 'モデル {model} はバニラ武器のモデルと同じ名前です。バニラ武器の見た目も置き換わります。', model=model)
    elif scan.assets and not game_model:
        add(ERROR, '武器モデル {model}.ydr がフォルダにありません。モデル名かフォルダを確認してください。', model=model)
    if scan.truncated:
        add(WARNING, 'ファイルが多すぎるため、途中で探すのをやめました。武器のフォルダだけを選んでください。')
    for d in scan.duplicates:
        add(WARNING, '同じ名前のファイルが複数あります。先に見つけた方を使います: {path}', path=d)

    # --- コンポーネント
    vanilla_components = {}
    for n in lib.component_names():
        try:
            vanilla_components[lib.component(n).internal_name.upper()] = lib.component(n)
        except MetaError:
            pass
    used_models = {model}
    seen: set[str] = set()
    defaults: dict[str, list[str]] = {}
    for c in project.components:
        label = c.name or c.template
        try:
            ct = lib.component(c.template)
        except MetaError as e:
            add(ERROR, 'コンポーネント {name}: テンプレート {tpl} を読めません: {reason}', name=label, tpl=c.template,
                reason=str(e))
            continue
        if not c.name:
            add(ERROR, 'コンポーネント名が空です(テンプレート {tpl})。', tpl=c.template)
        elif not _ID_RE.match(c.name):
            add(ERROR, 'コンポーネント名に使えない文字があります(半角英数字と _ のみ): {name}', name=c.name)
        elif c.name.upper() in seen:
            add(ERROR, 'コンポーネント名が重複しています: {name}', name=c.name)
        seen.add(c.name.upper())
        cmodel = c.model.strip().lower()
        vanilla = vanilla_components.get(c.name.upper())
        if vanilla is not None and cmodel != vanilla.model.lower():
            add(WARNING, 'コンポーネント名 {name} はバニラと同じです。バニラの部品の定義を上書きするので、別の名前を推奨します。',
                name=c.name)
        bone = component_bone(c, ct, tpl)
        if c.bone.strip() and not _ID_RE.match(c.bone.strip()):
            add(ERROR, 'コンポーネント {name}: ボーン名に使えない文字があります(半角英数字と _ のみ): {bone}', name=label, bone=c.bone)
        elif not bone:
            add(ERROR, 'コンポーネント {name}: 取り付けボーンが分かりません。ボーン名を入力してください。', name=label)
        elif c.default:
            defaults.setdefault(bone, []).append(label)
        if cmodel:
            used_models.add(cmodel)
            if not _MODEL_RE.match(cmodel):
                add(ERROR, 'コンポーネント {name}: モデル名に使えない文字があります: {model}', name=label, model=c.model)
            elif f'{cmodel}.ydr' not in by_key and cmodel != ct.model.lower():
                add(WARNING, 'コンポーネント {name}: モデル {model}.ydr がフォルダにありません。', name=label, model=cmodel)
        elif ct.model:
            add(WARNING, 'コンポーネント {name}: モデル名が空です。部品は表示されません。', name=label)
        if ct.is_clip and c.clip_size is not None and c.clip_size <= 0:
            add(ERROR, 'コンポーネント {name}: 装弾数は 1 以上にしてください。', name=label)
        if c.lod <= 0:
            add(ERROR, 'コンポーネント {name}: LOD 距離は 1 以上にしてください。', name=label)
    for bone, names in defaults.items():
        if len(names) > 1:
            add(WARNING, 'ボーン {bone} に「最初から装着」が複数あります: {names}', bone=bone, names=', '.join(names))

    # --- どこからも使われないファイル
    for a in assets:
        if a.ext in ('.ydr', '.ytd') and a.base not in used_models:
            add(WARNING, '{file} はどの武器・コンポーネントにも割り当てられていません(コピーはされます)。', file=a.name)

    if project.slot_order is None:
        add(INFO, '武器ホイールの並び順は書き出し時に自動で採番します。')
    return out

