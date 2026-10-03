"""ホイールを押したまま上下に動かして送る(ブラウザの自動スクロール)の速さの計算。Qt に依存しない。"""
from __future__ import annotations

DEAD_ZONE = 8       # 押した位置からこの距離(px)までは動かさない(手ぶれ対策)
GAIN = 0.12         # 遊びを超えた 1px あたり、1 回(約 16ms)に送る量(px)
MAX_STEP = 60.0     # 1 回に送る量の上限(px)


def step(offset: float) -> float:
    """押した位置からのカーソルの縦のずれ(下が正)から、1 回に送る量(px、下が正)を返す。"""
    over = abs(offset) - DEAD_ZONE
    if over <= 0:
        return 0.0
    amount = min(MAX_STEP, over * GAIN)
    return amount if offset > 0 else -amount


class Accumulator:
    """1 未満の端数を持ち越して、スクロールバーの整数の目盛りに直す。"""

    def __init__(self) -> None:
        self.rest = 0.0

    def take(self, amount: float, unit: float = 1.0) -> int:
        """amount(px)を unit(目盛り 1 つあたりの px)で割り、整数ぶんを返して端数を残す。"""
        self.rest += amount / max(unit, 1.0)
        whole = int(self.rest)      # 0 に向けて切り捨て(上下どちらでも端数を残す)
        self.rest -= whole
        return whole
