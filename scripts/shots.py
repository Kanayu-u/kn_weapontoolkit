"""画面を一通り操作してスクリーンショットを撮り、最後に実際に書き出す(GUI の通し確認と README 用)。

    .venv\\Scripts\\python scripts\\shots.py <出力フォルダ> [ja|en] [dark|light] [作業フォルダ]
設定とサンプルのモデルは一時フォルダに作るので、利用者の設定には触らない。
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

out = Path(sys.argv[1]).resolve()
lang = sys.argv[2] if len(sys.argv) > 2 else 'ja'
mode = sys.argv[3] if len(sys.argv) > 3 else 'dark'
out.mkdir(parents=True, exist_ok=True)

# README 用は個人のユーザー名がパスに写らない場所を第4引数で指定する
work = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(tempfile.mkdtemp(prefix='kwtk_shots_'))
work.mkdir(parents=True, exist_ok=True)
os.environ['KN_WTK_DATA'] = str(work / 'data')
(work / 'data').mkdir(exist_ok=True)
(work / 'data' / 'settings.json').write_text('{"language": "%s", "theme": "%s"}' % (lang, mode), encoding='utf-8')

# 日本語と空白を含むパスに置く(元ツールが読めなかった条件)
src = work / 'デスクトップ' / 'my weapon'
src.mkdir(parents=True)
for n in ['w_ar_m4a1.ydr', 'w_ar_m4a1_hi.ydr', 'w_ar_m4a1.ytd', 'w_ar_m4a1+hi.ytd', 'w_ar_m4a1_mag1.ydr',
          'w_ar_m4a1_mag2.ydr', 'w_ar_m4a1_supp.ydr', 'w_ar_m4a1_scope.ydr', 'w_ar_m4a1_scope.ytd', 'extra_prop.ydr']:
    (src / n).write_bytes(b'RSC7')
dst = work / '書き出し 先'
dst.mkdir()

from kn_weapontoolkit.ui.app import create  # noqa: E402

app, win = create(sys.argv[:1])
win.show()


def shot(name: str) -> None:
    for _ in range(5):
        app.processEvents()
    win.grab().save(str(out / f'{name}_{lang}_{mode}.png'))


p = win.state.project
# 1. 武器: 元ツールで meta が出なかったブルパップで通す
win.weapon_page.set_import_dir(str(src))
win.weapon_page.template.setCurrentText('WEAPON_BULLPUPRIFLE')
win.weapon_page._on_template(0)
win.weapon_page.display_name.setText('M4A1')
win.weapon_page.weapon_id.setText('WEAPON_M4A1')
win.weapon_page._on_edit()
assert p.model == 'w_ar_m4a1', p.model
assert p.template == 'WEAPON_BULLPUPRIFLE'
shot('1_weapon')

# 2. 性能
win.show_page(1)
ed = win.stats_page._editors['Damage'][1]
ed.setText('38')
ed.textEdited.emit('38')
assert p.fields == {'Damage': '38'}, p.fields
shot('2_stats')

# 3. コンポーネント
win.show_page(2)
win.components_page.detect()
assert [c.name for c in p.components] == ['COMPONENT_M4A1_CLIP_01', 'COMPONENT_M4A1_CLIP_02', 'COMPONENT_M4A1_SCOPE',
                                          'COMPONENT_M4A1_SUPP'], [c.name for c in p.components]
assert win.components_page.list.count() == 4
# 一覧の選択と編集対象がずれないこと(元ツールは逆順で別の部品を編集していた)
win.components_page.list.setCurrentRow(3)
assert win.components_page.name.text() == 'COMPONENT_M4A1_SUPP'
win.components_page.list.setCurrentRow(1)
win.components_page.clip.setValue(45)
assert p.components[1].clip_size == 45 and p.components[0].clip_size == 30
win.components_page.list.setCurrentRow(0)
shot('3_components')

# 4. 書き出し
win.show_page(3)
win.export_page.out_edit.setText(str(dst))
win.export_page.refresh()
shot('4_export_before')
levels = [i.level for i in win.export_page.issues()]
assert 'error' not in levels, [i.message for i in win.export_page.issues()]
win.export_page.export()
shot('4_export_after')
target = dst / 'weapon_m4a1'
files = sorted(str(f.relative_to(target)).replace('\\', '/') for f in target.rglob('*') if f.is_file())
print('\n'.join(files))
assert 'meta/weapons.meta' in files and 'meta/weaponcomponents.meta' in files and 'stream/w_ar_m4a1.ydr' in files
assert p.slot_order == 400, p.slot_order
print('issues:', [(i.level, i.message) for i in win.export_page.issues()])

# 5. テンプレートの取り込み(テスト用の meta を作って取り込む)。完了のメッセージ箱は止まるので差し替える
from PySide6.QtWidgets import QMessageBox  # noqa: E402

sys.path.insert(0, str(ROOT / 'tests'))
import test_importer as ti  # noqa: E402

addon = work / 'アドオン 武器' / 'meta'
addon.mkdir(parents=True)
for fn, text in (('weapons.meta', ti.WEAPONS_META), ('weaponcomponents.meta', ti.COMPONENTS_META),
                 ('weaponanimations.meta', ti.ANIMS_META), ('pedpersonality.meta', ti.PERSONALITY_META)):
    (addon / fn).write_text(text, encoding='utf-8')
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
# テンプレートを変えるときの確認(性能の変更を破棄するか)には「はい」と答える
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
from kn_weapontoolkit.ui.import_dialog import ImportDialog  # noqa: E402

dlg = ImportDialog(win.state, win)
dlg.show()
dlg.load(str(addon.parent))
assert dlg.weapons.topLevelItemCount() == 2 and dlg.components.topLevelItemCount() == 2
for _ in range(5):
    app.processEvents()
dlg.grab().save(str(out / f'5_import_{lang}_{mode}.png'))
dlg.do_import()
names = [win.weapon_page.template.itemText(i) for i in range(win.weapon_page.template.count())]
assert 'WEAPON_TESTRIFLE' in names and 'WEAPON_HEAVYSNIPER_MK2' in names, len(names)
assert win.state.lib.weapon('WEAPON_TESTRIFLE').source == 'user'

# 6. MK2 のテンプレートでは、マズルがバニラどおり WAPSupp_2 になる(自動の表示)
win.show_page(0)
win.weapon_page.template.setCurrentText('WEAPON_CARBINERIFLE_MK2')
win.weapon_page._on_template(0)
assert 'WEAPON_CARBINERIFLE_MK2' == p.template
win.show_page(2)
win.components_page.list.setCurrentRow(3)      # COMPONENT_M4A1_SUPP (COMPONENT_AT_AR_SUPP)
ph = win.components_page.bone.lineEdit().placeholderText()
assert 'WAPSupp_2' in ph, ph
win.show_page(0)
win.weapon_page.template.setCurrentText('WEAPON_HEAVYSNIPER_MK2')
win.weapon_page._on_template(0)
assert 'WEAPON_HEAVYSNIPER' in win.weapon_page.template_note.text(), win.weapon_page.template_note.text()
shot('6_weapon_borrowed')
print('OK', work)
win.state.dirty = False
win.close()
