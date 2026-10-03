"""「性能」ページの主な項目。表示名と説明は確かなものだけを載せる(不明な項目は一覧表で生のタグ名のまま編集する)。"""
from __future__ import annotations

from .gamedata import AMMO_TYPES, AUDIO_ITEMS, DAMAGE_TYPES, EXPLOSION_TAGS, FIRE_TYPES, FLASH_FX
from .i18n import N_

# (タグ, 表示名, 説明, 候補一覧 or None)
BASIC_FIELDS: list[tuple[str, str, str, list[str] | None]] = [
    ('Audio', N_('発砲音'), N_('発砲音などの音声セット。'), AUDIO_ITEMS),
    ('AmmoInfo', N_('弾薬の種類'), N_('使う弾薬。同じ弾薬の武器どうしで残弾を共有します。'), AMMO_TYPES),
    ('DamageType', N_('ダメージの種類'), N_('BULLET(弾)/ MELEE(近接)/ EXPLOSIVE(爆発)など。'), DAMAGE_TYPES),
    ('FireType', N_('発射方式'), N_('INSTANT_HIT は弾が即座に当たる(普通の銃)。PROJECTILE は弾が実体として飛ぶ(ロケット・グレネード)。DELAYED_HIT はスナイパーライフル、VOLUMETRIC_PARTICLE は噴射(消火器・ガソリン缶)が使う方式。弾薬の種類と組み合わせて使います。'), FIRE_TYPES),
    ('Explosion/Default', N_('着弾時の爆発'), N_('弾が当たった所で起こす爆発。バニラの普通の銃は DONTCARE、レールガンは EXP_TAG_RAILGUN。ダメージの種類を EXPLOSIVE にしないと爆発しません。'), EXPLOSION_TAGS),
    ('Fx/FlashFx', N_('発砲・噴射のエフェクト'), N_('撃ったときに出るエフェクトの名前。消火器では噴射の見た目にあたります。'), FLASH_FX),
    ('Damage', N_('ダメージ'), N_('1発(1撃)あたりの基本ダメージ。'), None),
    ('HeadShotDamageModifierPlayer', N_('ヘッドショット倍率'), N_('プレイヤーの頭に当たったときのダメージ倍率。'), None),
    ('WeaponRange', N_('射程'), N_('弾が届く最大距離(m)。'), None),
    ('ClipSize', N_('装弾数'), N_('マガジンの部品を付けないときの装弾数。'), None),
    ('TimeBetweenShots', N_('射撃間隔(秒)'), N_('次の弾を撃てるまでの時間。ただし実機では、この値を変えても連射の速さは変わりませんでした(カービンとピストルで確認。連射の速さは射撃動作で決まる)。連射の速さは「射撃動作の速度倍率」で変えてください。'), None),
    ('AnimReloadRate', N_('リロード速度の倍率'), N_('リロード動作の再生速度。大きいほど速くなります。'), None),
    ('AccuracySpread', N_('弾のばらつき'), N_('大きいほど弾が散ります。'), None),
    ('RecoilShakeAmplitude', N_('反動(画面の揺れ)'), N_('撃ったときの画面の揺れの強さ。'), None),
    ('Speed', N_('弾速'), N_('弾の速さ。'), None),
    ('BulletsInBatch', N_('1回に出る弾の数'), N_('ショットガンのように、1回の射撃で出る弾の数。'), None),
    ('BatchSpread', N_('同時発射の広がり'), N_('1回に複数の弾を出すときの広がり。'), None),
    ('Force', N_('衝撃力'), N_('当たった物体を押す力。'), None),
    ('DamageFallOffRangeMin', N_('威力減衰の開始距離'), N_('この距離から威力が下がり始めます。'), None),
    ('DamageFallOffRangeMax', N_('威力減衰の終了距離'), N_('この距離で威力が最小になります。'), None),
    ('DamageFallOffModifier', N_('減衰後の威力倍率'), N_('減衰しきったときのダメージ倍率。'), None),
]
BASIC_TAGS = [f[0] for f in BASIC_FIELDS]
