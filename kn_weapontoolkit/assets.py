"""取り込みフォルダのモデル・テクスチャを集める。パスは pathlib で扱う(日本語や空白を含んでいてよい)。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

STREAM_EXTS = ('.ydr', '.ytd', '.yft', '.ycd')
MAX_FILES = 2000    # 誤ってドライブ直下などを選んだときの歯止め
MAX_VISITED = 50000  # モデル以外も含めて見たファイル数の上限(モデルが少ない巨大なフォルダで固まらないように)


@dataclass(frozen=True)
class Asset:
    name: str       # ファイル名(元の大文字小文字のまま)
    path: Path

    @property
    def key(self) -> str:
        return self.name.lower()

    @property
    def ext(self) -> str:
        return os.path.splitext(self.key)[1]

    @property
    def base(self) -> str:
        """対応するモデル名(小文字)。w_x_hi.ydr / w_x+hi.ytd はどちらも w_x。"""
        stem = os.path.splitext(self.key)[0]
        if self.ext in ('.ydr', '.yft') and stem.endswith('_hi'):
            return stem[:-3]
        if self.ext == '.ytd' and stem.endswith('+hi'):
            return stem[:-3]
        return stem

    @property
    def is_base_model(self) -> bool:
        """weaponarchetypes に載せる本体モデル(_hi は載せない)。"""
        return self.ext == '.ydr' and not os.path.splitext(self.key)[0].endswith('_hi')


@dataclass
class ScanResult:
    assets: list[Asset]
    duplicates: list[str]       # 同名で2つ目以降に見つかったファイル(使わない)
    truncated: bool = False


def scan(directory: str | Path) -> ScanResult:
    """フォルダ以下を再帰的に探す。同名ファイルは先に見つけたもの(直下が先、サブフォルダは名前順にたどる)を使う。"""
    root = Path(directory)
    found: dict[str, Asset] = {}
    dups: list[str] = []
    truncated = False
    visited = 0
    if not directory or not root.is_dir():
        return ScanResult([], [])
    for cur, dirs, files in os.walk(root):
        dirs.sort(key=str.lower)
        visited += len(files)
        if visited > MAX_VISITED:
            truncated = True
            break
        for fn in sorted(files, key=str.lower):
            if os.path.splitext(fn)[1].lower() not in STREAM_EXTS:
                continue
            a = Asset(fn, Path(cur) / fn)
            if a.key in found:
                dups.append(str(a.path))
                continue
            if len(found) >= MAX_FILES:
                truncated = True
                break
            found[a.key] = a
        if truncated:
            break
    return ScanResult(sorted(found.values(), key=lambda a: a.key), dups, truncated)
