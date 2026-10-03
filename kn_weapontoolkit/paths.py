"""テンプレートと設定の置き場を一箇所で決める。作業フォルダ(カレントディレクトリ)には依存しない。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from . import APP_NAME


def is_frozen() -> bool:
    return bool(getattr(sys, 'frozen', False))


def app_dir() -> Path:
    """exe 化時は exe のあるフォルダ、開発時はリポジトリ直下。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def templates_dir() -> Path:
    """テンプレートの場所。KN_WTK_TEMPLATES で差し替え可(テスト用)。

    exe の隣の templates/ を優先する(ユーザーが足せる場所)。無ければ同梱物の展開先を見る。
    """
    override = os.environ.get('KN_WTK_TEMPLATES')
    if override:
        return Path(override)
    beside = app_dir() / 'templates'
    if beside.is_dir() or not is_frozen():
        return beside
    return Path(getattr(sys, '_MEIPASS', app_dir())) / 'templates'


def user_templates_dir() -> Path:
    """取り込んだテンプレートの置き場(同梱より優先)。アプリを更新しても消えない場所。"""
    return data_dir() / 'templates'


def template_roots() -> list[Path]:
    return [user_templates_dir(), templates_dir()]


def data_dir() -> Path:
    """設定の置き場。KN_WTK_DATA で差し替え可(テスト用)。"""
    override = os.environ.get('KN_WTK_DATA')
    if override:
        base = Path(override)
    elif os.name == 'nt':
        base = Path(os.environ.get('APPDATA') or Path.home() / 'AppData' / 'Roaming') / APP_NAME
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base
