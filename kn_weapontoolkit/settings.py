"""アプリの設定。JSON 1ファイル、書き込みは一時ファイル経由で原子的に。"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from . import paths

LANGUAGES = ['', 'ja', 'en']    # '' = OS に合わせる
THEMES = ['system', 'dark', 'light']
FIRST_SLOT = 400                # 元ツールと同じ開始番号

DEFAULTS: dict[str, Any] = {
    'language': '',
    'theme': 'system',
    'next_slot': FIRST_SLOT,    # 次に採番する武器ホイールの並び順
    'last_import_dir': '',
    'last_export_dir': '',
    'last_project_dir': '',
}


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = path or paths.data_dir() / 'settings.json'
        self.data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        for k, default in DEFAULTS.items():
            v = raw.get(k)
            if isinstance(v, type(default)) and not isinstance(v, bool):
                self.data[k] = v
        if self.data['language'] not in LANGUAGES:
            self.data['language'] = ''
        if self.data['theme'] not in THEMES:
            self.data['theme'] = 'system'
        if self.data['next_slot'] < 1:
            self.data['next_slot'] = FIRST_SLOT

    def save(self) -> None:
        tmp = ''
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='settings.', suffix='.tmp', dir=self.path.parent)
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            # 設定が保存できなくても作業は続けられる。書きかけの一時ファイルは残さない
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if self.data.get(key) != value:
            self.data[key] = value
            self.save()

    def take_slot(self) -> int:
        """並び順を1つ採番する(武器ごとに重ならないよう、使うたびに進める)。"""
        n = int(self.data['next_slot'])
        self['next_slot'] = n + 1
        return n
