"""画面どうしで共有する編集中の状態。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .. import assets
from ..model import Project
from ..settings import Settings
from ..templates import TemplateLibrary, WeaponTemplate
from ..xmlio import MetaError


class AppState(QObject):
    changed = Signal()              # プロジェクトの中身が変わった
    project_replaced = Signal()     # 新規・読込で丸ごと入れ替わった(各ページは入力欄を作り直す)
    template_changed = Signal()     # 武器テンプレートが変わった
    assets_changed = Signal()       # 取り込みフォルダを読み直した
    templates_changed = Signal()    # テンプレートを取り込んで一覧が変わった

    def __init__(self, settings: Settings, lib: TemplateLibrary):
        super().__init__()
        self.settings = settings
        self.lib = lib
        self.project = Project()
        self.scan = assets.ScanResult([], [])
        self.path: Path | None = None
        self.dirty = False

    def touch(self) -> None:
        self.dirty = True
        self.changed.emit()

    def template(self) -> WeaponTemplate | None:
        try:
            return self.lib.weapon(self.project.template)
        except MetaError:
            return None

    def rescan(self) -> None:
        self.scan = assets.scan(self.project.import_dir)
        self.assets_changed.emit()

    def set_project(self, project: Project, path: Path | None) -> None:
        self.project = project
        self.path = path
        self.dirty = False
        self.scan = assets.scan(project.import_dir)
        self.project_replaced.emit()
        self.assets_changed.emit()
        self.changed.emit()
