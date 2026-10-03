# Third-party notices

## このリポジトリのコード
`kn_weapontoolkit/`・`tests/`・`scripts/` のコードは新しく書いたもので、MIT ライセンスです(`LICENSE`)。

## templates/ (MIT ライセンスの対象外)
`templates/` 以下の meta ファイルは、Grand Theft Auto V のゲームデータ(Rockstar Games)を元に、
次のプロジェクトとその貢献者が武器ごとに切り出したものです。本リポジトリではそれを取り込み、壊れていた
ファイルを修正して同梱しています(修正内容は `CHANGELOG.md`)。

| 出どころ | 作者 | 入手先 |
|---|---|---|
| vWeaponsToolkit | Robbster (rubbertoe98) | https://github.com/rubbertoe98/vWeaponsToolkit |
| FiveM Addon Weapon Tool Kit(上記のフォーク) | Hxrv3y と貢献者 | https://github.com/Hxrv3y/FiveM-Addon-Weapon-Tool-Kit |

さらに、次の公開データからバニラの定義を切り出して、武器テンプレート 38 種と部品テンプレート 328 種を追加しました
(`scripts/build_templates.py`)。各武器テンプレートの `template.json` に出どころと、動作・構え方を借りた武器を記録しています。

| 出どころ | 内容 | 入手先 |
|---|---|---|
| weapon-merger (votrinhan88) のバニラ meta の控え(1.70) | 武器の定義(weapon*.meta)と、各武器の取り付けボーン | https://github.com/votrinhan88/weapon-merger |
| snag_weapon_metas (CyCoSnag。リポジトリは GPL-3.0 として配布) | 部品の定義(weaponcomponents) | https://github.com/CyCoSnag/snag_weapon_metas |

上の 2 つのリポジトリにはライセンスの記載がありません。`templates/` は本リポジトリの MIT ライセンスの対象には
含めておらず、権利は元の権利者にあります。権利者から申し出があれば、同梱をやめて利用者が自分で用意する方式に
切り替えます。

本ツールは Rockstar Games・Take-Two Interactive・Cfx.re とは関係ありません。

## 配布物(dist/kn_weapontoolkit)に含まれるソフトウェア

| ソフトウェア | ライセンス | 入手先 |
|---|---|---|
| Python | PSF License | https://www.python.org/ |
| Qt 6 / PySide6 | LGPL-3.0 | https://www.qt.io/ , https://code.qt.io/ |

Qt と PySide6 は動的ライブラリ(`_internal/PySide6/` 配下の DLL / pyd)として同梱しており、利用者は互換のある
別ビルドへ差し替えられます。ソースコードは上記の入手先から取得できます。Qt 標準ダイアログの翻訳
(`qtbase_*.qm`)も Qt に含まれるもので、同じ LGPL-3.0 です。
