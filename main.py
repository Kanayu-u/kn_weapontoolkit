"""KN Weapon Toolkit エントリポイント。引数にプロジェクト(.kwtk.json)かモデルのフォルダを渡すと開く。

`--selfcheck <結果ファイル>`: 画面を出さずにテンプレートの読み込みと書き出しを試し、結果をファイルに書く(ビルドの確認用)。
"""
import sys


def selfcheck(report_path: str) -> int:
    import tempfile
    import traceback
    from pathlib import Path
    lines: list[str] = []
    code = 1
    try:
        from kn_weapontoolkit import __version__, assets, exporter, paths
        from kn_weapontoolkit.model import Project
        from kn_weapontoolkit.templates import TemplateLibrary
        lib = TemplateLibrary(paths.template_roots())
        problems = lib.scan_problems()
        lines.append(f'version {__version__}')
        lines.append(f'templates {paths.templates_dir()} (+ {paths.user_templates_dir()})')
        lines.append(f'weapons {len(lib.weapon_names())} components {len(lib.component_names())}')
        lines += [f'problem {name}: {reason}' for name, reason in problems]
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'モデル'
            src.mkdir()
            (src / 'w_ar_selfcheck.ydr').write_bytes(b'RSC7')
            p = Project(template=lib.weapon_names()[0], weapon_id='WEAPON_SELFCHECK', model='w_ar_selfcheck')
            target = exporter.export(p, lib, assets.scan(src).assets, d)
            lines.append(f'exported {len([f for f in target.rglob("*") if f.is_file()])} files')
        if not problems:
            lines.append('OK')
            code = 0
    except Exception:
        lines.append(traceback.format_exc())
    Path(report_path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return code


def run() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == '--selfcheck':
        return selfcheck(sys.argv[2])
    from kn_weapontoolkit.ui.app import main as gui_main
    return gui_main()


if __name__ == '__main__':
    sys.exit(run())
