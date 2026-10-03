"""English. Keys are the Japanese source strings."""

T: dict[str, str] = {
    # --- checks
    '武器 ID が空です。': 'The weapon ID is empty.',
    '表示名が空です。': 'The display name is empty.',
    'リソース名が空です。': 'The resource name is empty.',
    'LOD 距離は 1 以上にしてください。': 'LOD distance must be 1 or more.',
    '射撃動作の速度倍率は 0 より大きくしてください。': 'The fire animation rate must be greater than 0.',
    'モデルのフォルダが選ばれていません。': 'No model folder is selected.',
    '武器モデル名が空です。': 'The weapon model name is empty.',
    'ファイルが多すぎるため、途中で探すのをやめました。武器のフォルダだけを選んでください。':
        'Too many files; the search stopped early. Select only the folder of this weapon.',
    '同じ名前のファイルが複数あります。先に見つけた方を使います: {path}':
        'Several files share this name. The first one found is used: {path}',
    '武器ホイールの並び順は書き出し時に自動で採番します。':
        'The weapon wheel order number will be assigned automatically on export.',
    'テンプレート {name} に weaponanimations.meta がありません。動作の定義なしで書き出します。':
        'Template {name} has no weaponanimations.meta. Exporting without animation definitions.',
    'テンプレート {name} に pedpersonality.meta がありません。構え方の定義なしで書き出します。':
        'Template {name} has no pedpersonality.meta. Exporting without movement mode definitions.',
    'テンプレート {name} を読めません: {reason}': 'Cannot read template {name}: {reason}',
    '武器 ID に使えない文字があります(半角英数字と _ のみ): {id}':
        'The weapon ID contains invalid characters (letters, digits and _ only): {id}',
    'リソース名に使えない文字があります(半角英数字と _ - のみ): {name}':
        'The resource name contains invalid characters (letters, digits, _ and - only): {name}',
    'フォルダにモデル(.ydr)やテクスチャ(.ytd)が見つかりません: {dir}':
        'No models (.ydr) or textures (.ytd) found in the folder: {dir}',
    '武器モデル名に使えない文字があります: {model}': 'The weapon model name contains invalid characters: {model}',
    'コンポーネント名が空です(テンプレート {tpl})。': 'A component name is empty (template {tpl}).',
    'コンポーネント名 {name} はバニラと同じです。バニラの部品の定義を上書きするので、別の名前を推奨します。':
        'Component name {name} is the same as a vanilla one. It overrides the vanilla definition, so a different name '
        'is recommended.',
    'コンポーネント {name}: 取り付けボーンが分かりません。ボーン名を入力してください。':
        'Component {name}: the attach bone is unknown. Enter a bone name.',
    'コンポーネント {name}: 装弾数は 1 以上にしてください。': 'Component {name}: clip size must be 1 or more.',
    'コンポーネント {name}: LOD 距離は 1 以上にしてください。': 'Component {name}: LOD distance must be 1 or more.',
    'ボーン {bone} に「最初から装着」が複数あります: {names}':
        'Bone {bone} has more than one "attached by default" component: {names}',
    '{file} はどの武器・コンポーネントにも割り当てられていません(コピーはされます)。':
        '{file} is not assigned to the weapon or any component (it is still copied).',
    '武器 ID は WEAPON_ で始めるのが通例です: {id}': 'Weapon IDs conventionally start with WEAPON_: {id}',
    '武器 ID に小文字が含まれています。大文字にそろえるのが通例です: {id}':
        'The weapon ID contains lowercase letters. Upper case is the convention: {id}',
    '武器 ID {id} はバニラ武器と同じ名前です。バニラ武器の定義を上書きします。':
        'Weapon ID {id} is the name of a vanilla weapon. It will override the vanilla definition.',
    '項目 {tag} はテンプレート {name} に無いため書き出されません。':
        'Field {tag} does not exist in template {name} and will not be written.',
    'コンポーネント {name}: テンプレート {tpl} を読めません: {reason}':
        'Component {name}: cannot read template {tpl}: {reason}',
    'コンポーネント名に使えない文字があります(半角英数字と _ のみ): {name}':
        'The component name contains invalid characters (letters, digits and _ only): {name}',
    'コンポーネント {name}: モデル名に使えない文字があります: {model}':
        'Component {name}: the model name contains invalid characters: {model}',
    'コンポーネント {name}: モデル名が空です。部品は表示されません。':
        'Component {name}: the model name is empty. The part will not be visible.',
    '項目 {tag} の値が数値ではありません: {value}': 'The value of field {tag} is not a number: {value}',
    '武器モデル {model}.ydr がフォルダにありません。モデル名かフォルダを確認してください。':
        'Weapon model {model}.ydr is not in the folder. Check the model name or the folder.',
    'モデル {model} はバニラ武器のモデルと同じ名前です。バニラ武器の見た目も置き換わります。':
        'Model {model} has the same name as a vanilla weapon model. That vanilla weapon will look replaced too.',
    'ゲームに入っているモデル {model} を使います(モデルのファイルは同梱しません)。':
        'Using the in-game model {model} (no model files are bundled).',
    'コンポーネント名が重複しています: {name}': 'Duplicate component name: {name}',
    'コンポーネント {name}: モデル {model}.ydr がフォルダにありません。':
        'Component {name}: model {model}.ydr is not in the folder.',
    '項目 {tag} が空です。': 'Field {tag} is empty.',
    '{model}.ytd がありません。テクスチャがモデルに埋め込まれていれば問題ありません。':
        '{model}.ytd is missing. This is fine if the textures are embedded in the model.',
    '{model}_hi.ydr がありません。手に持ったときも通常モデルが使われます。':
        '{model}_hi.ydr is missing. The normal model is used when held as well.',

    # --- stat fields
    '発砲音': 'Fire audio',
    '発砲音などの音声セット。': 'The audio set used for firing and other sounds.',
    '弾薬の種類': 'Ammo type',
    '使う弾薬。同じ弾薬の武器どうしで残弾を共有します。': 'The ammo it uses. Weapons with the same ammo share the reserve.',
    'ダメージの種類': 'Damage type',
    'BULLET(弾)/ MELEE(近接)/ EXPLOSIVE(爆発)など。': 'BULLET / MELEE / EXPLOSIVE and so on.',
    'ダメージ': 'Damage',
    '1発(1撃)あたりの基本ダメージ。': 'Base damage per shot (or hit).',
    'ヘッドショット倍率': 'Headshot multiplier',
    'プレイヤーの頭に当たったときのダメージ倍率。': 'Damage multiplier when hitting a player in the head.',
    '射程': 'Range',
    '弾が届く最大距離(m)。': 'Maximum distance the bullet travels (m).',
    '装弾数': 'Clip size',
    'マガジンの部品を付けないときの装弾数。': 'Clip size when no magazine component is attached.',
    '射撃間隔(秒)': 'Time between shots (s)',
    '次の弾を撃てるまでの時間。ただし実機では、この値を変えても連射の速さは変わりませんでした(カービンとピストルで確認。連射の速さは射撃動作で決まる)。連射の速さは「射撃動作の速度倍率」で変えてください。': 'Time until the next shot. In game, changing this did not change the fire rate (confirmed on the Carbine and the Pistol; the fire rate follows the fire animation). Use the fire animation rate instead.',
    '射撃間隔を変えても、連射の速さは変わらないことがあります(バニラのカービンとピストルで確認)。連射の速さを変えるには「射撃動作の速度倍率」を使ってください。': 'Changing the time between shots may not change the fire rate (confirmed on the vanilla Carbine and Pistol). Use the fire animation rate to change it.',
    'リロード速度の倍率': 'Reload rate',
    'リロード動作の再生速度。大きいほど速くなります。': 'Playback rate of the reload animation. Larger is faster.',
    '弾のばらつき': 'Accuracy spread',
    '大きいほど弾が散ります。': 'Larger values scatter shots more.',
    '反動(画面の揺れ)': 'Recoil (camera shake)',
    '撃ったときの画面の揺れの強さ。': 'Strength of the camera shake when firing.',
    '弾速': 'Bullet speed',
    '弾の速さ。': 'Speed of the bullet.',
    '1回に出る弾の数': 'Bullets per shot',
    'ショットガンのように、1回の射撃で出る弾の数。': 'Number of bullets fired per shot, as with shotguns.',
    '同時発射の広がり': 'Batch spread',
    '1回に複数の弾を出すときの広がり。': 'Spread when several bullets are fired per shot.',
    '衝撃力': 'Force',
    '当たった物体を押す力。': 'Force applied to whatever is hit.',
    '威力減衰の開始距離': 'Damage falloff start',
    'この距離から威力が下がり始めます。': 'Damage starts dropping from this distance.',
    '威力減衰の終了距離': 'Damage falloff end',
    'この距離で威力が最小になります。': 'Damage reaches its minimum at this distance.',
    '減衰後の威力倍率': 'Falloff damage multiplier',
    '減衰しきったときのダメージ倍率。': 'Damage multiplier at full falloff.',

    # --- app
    '予期しないエラーが起きました。作業内容は保存してから続けてください。':
        'An unexpected error occurred. Save your work before continuing.',
    'テンプレートが見つかりません。\n{path}\nアプリのフォルダに templates フォルダがあるか確認してください。':
        'Templates not found.\n{path}\nMake sure the templates folder is in the application folder.',

    # --- components page
    '追加': 'Add',
    '削除': 'Remove',
    'ファイルから自動検出': 'Detect from files',
    '武器モデル名で始まる部品モデル(_mag1 / _supp / _scope など)からコンポーネントを作ります。':
        'Creates components from part models whose names start with the weapon model name (_mag1 / _supp / _scope …).',
    'テンプレートに元からある部品を残す': 'Keep the parts defined by the template',
    'テンプレート武器が持つバニラの部品定義を残します。同じボーンに部品を追加した場合は、追加した方に置き換わります。':
        'Keeps the vanilla parts the template weapon defines. If you add a part on the same bone, yours replaces them.',
    'スクリプトから部品を指す名前。COMPONENT_ で始まる大文字の英数字。バニラと同じ名前は避けてください。':
        'The name scripts use for this part. Upper-case, starting with COMPONENT_. Avoid vanilla names.',
    '部品のモデル名(.ydr の拡張子なし)。': 'Model name of the part (.ydr without the extension).',
    '武器の弾薬のまま': 'Same as the weapon',
    'このマガジンを付けたときだけ使う弾薬(曳光弾など)。空なら武器の弾薬のまま。':
        'Ammo used only while this magazine is attached (tracer etc.). Empty keeps the weapon ammo.',
    '部品を取り付ける武器モデル側のボーン。空ならテンプレートから自動で決めます。':
        'The bone on the weapon model the part attaches to. Empty picks it from the template.',
    '最初から装着しておく': 'Attached by default',
    '武器を手に入れた時点で付いている部品にします。マガジンは通常1つをこれにします。':
        'The part is already attached when the weapon is obtained. Usually one magazine has this on.',
    'テンプレート': 'Template',
    'コンポーネント名': 'Component name',
    'モデル名': 'Model name',
    'LOD 距離': 'LOD distance',
    '弾薬': 'Ammo',
    '取り付けボーン': 'Attach bone',
    'テンプレートの部品 — {list}': 'Template parts — {list}',
    'コンポーネント': 'Components',
    'マガジンやサプレッサーなど、武器に付ける部品を定義します。無くても書き出せます。':
        'Define parts such as magazines and suppressors. You can export without any.',
    'このテンプレートに元からある部品はありません。': 'This template defines no parts of its own.',
    'コンポーネントのテンプレートがありません。': 'There are no component templates.',
    '自動検出': 'Detect',
    '新しく追加できる部品モデルは見つかりませんでした。\n武器モデル名({model})で始まる _mag1 / _mag2 / _supp / _scope / _afgrip / _flsh を探します。':
        'No new part models were found.\nIt looks for _mag1 / _mag2 / _supp / _scope / _afgrip / _flsh after the weapon '
        'model name ({model}).',
    '「追加」または「ファイルから自動検出」で部品を作ります。': 'Use "Add" or "Detect from files" to create parts.',
    '自動: {bone}': 'Auto: {bone}',
    'ボーン名を入力': 'Enter a bone name',
    'テンプレート {name} を読めません。': 'Cannot read template {name}.',
    'このテンプレートは弾薬の切り替えに対応していません。': 'This template does not support switching ammo.',

    # --- export page
    'エラー': 'Error',
    '注意': 'Warning',
    '情報': 'Info',
    '書き出しました: {path}(ファイル {n} 個)': 'Exported: {path} ({n} files)',
    '武器ホイールの並び順を自動で決める': 'Assign the weapon wheel order automatically',
    '武器ごとに重ならない番号を、書き出すときに割り当てます(次の番号は設定で変えられます)。':
        'Assigns a number that does not clash between weapons when exporting (the next number can be changed in Settings).',
    '書き出し先のフォルダ(この中にリソース名のフォルダを作ります)':
        'Output folder (a folder named after the resource is created inside)',
    '参照…': 'Browse…',
    '書き出す': 'Export',
    'フォルダを開く': 'Open folder',
    '書き出し先のフォルダを選ぶ': 'Select the output folder',
    '書き出し': 'Export',
    '問題が無いか点検してから、サーバーの resources に置けるフォルダとして保存します。':
        'Checks for problems, then saves a folder you can drop into the server resources.',
    '点検': 'Checks',
    '並び順': 'Order',
    '書き出し先': 'Output',
    'エラー {n} 件 — 直すまで書き出せません': 'Errors: {n} — fix them before exporting',
    '保存先: {path}': 'Will be saved to: {path}',
    '書き出し先のフォルダを選んでください。': 'Select an output folder.',
    '{path} は既にあります。中身を今回の書き出しで置き換えますか?':
        '{path} already exists. Replace its contents with this export?',
    'テンプレートに無いため書かなかった項目: {tags}': 'Fields not written because the template lacks them: {tags}',
    '作業用フォルダが消し残っています。手で削除してください: {names}':
        'Working folders were left behind. Please delete them by hand: {names}',
    '注意 {n} 件 — 書き出せます': 'Warnings: {n} — export is possible',
    '問題なし': 'No problems',
    '書き出せませんでした。\n{reason}': 'Export failed.\n{reason}',
    '問題は見つかりませんでした。': 'No problems found.',

    # --- main window
    'ファイル(&F)': '&File',
    '設定(&P)…': '&Settings…',
    '終了(&X)': 'E&xit',
    'ヘルプ(&H)': '&Help',
    'このアプリについて(&A)': '&About',
    '無題': 'Untitled',
    '変更が保存されていません。保存しますか?': 'You have unsaved changes. Save them?',
    '保存する': 'Save',
    '保存しない': "Don't save",
    'キャンセル': 'Cancel',
    'プロジェクトを開く': 'Open project',
    '武器プロジェクト (*{ext});;すべてのファイル (*)': 'Weapon project (*{ext});;All files (*)',
    'プロジェクトを保存': 'Save project',
    '武器プロジェクト (*{ext})': 'Weapon project (*{ext})',
    'このアプリについて': 'About',
    '<b>{name}</b> {version}<br><br>GTA V / FiveM のアドオン武器リソースを作るツールです。<br><br>Robbster 氏の vWeaponsToolkit と、Hxrv3y 氏によるフォーク(FiveM Addon Weapon Tool Kit)を参考に、新しく書き直したものです。テンプレートは両プロジェクトとその貢献者によるものを修正して同梱しています。<br><br><a href="{url}">{url}</a>':
        '<b>{name}</b> {version}<br><br>A tool for creating add-on weapon resources for GTA V / FiveM.<br><br>'
        'A new implementation modelled on vWeaponsToolkit by Robbster and its fork by Hxrv3y (FiveM Addon Weapon Tool '
        'Kit). The bundled templates come from those projects and their contributors, with fixes.<br><br>'
        '<a href="{url}">{url}</a>',
    '1. 武器': '1. Weapon',
    '2. 性能': '2. Stats',
    '3. コンポーネント': '3. Components',
    '4. 書き出し': '4. Export',
    '新規(&N)': '&New',
    '質問・不具合の報告・要望: {link}': 'Questions, bug reports and requests: {link}',
    '武器ホイールの並び順は 1 以上にしてください。': 'The weapon wheel order must be 1 or greater.',
    'コンポーネント {name}: ボーン名に使えない文字があります(半角英数字と _ のみ): {bone}': 'Component {name}: the bone name has invalid characters (letters, digits and _ only): {bone}',
    'ファイルが多すぎるため、途中で探すのをやめました。meta の入ったフォルダだけを選んでください。': 'Too many files; stopped searching partway. Select only the folder that contains the meta files.',
    'リセット': 'Reset',
    '選んだテンプレート・名前・フォルダ・部品・性能の変更をすべて消して、最初から作り直します。': 'Clear the template, names, folder, components and stat changes, and start over.',
    '開く(&O)…': '&Open…',
    '保存(&S)': '&Save',
    '名前を付けて保存(&A)…': 'Save &As…',
    '開けませんでした。\n{reason}': 'Could not open the project.\n{reason}',
    '保存できませんでした。\n{reason}': 'Could not save the project.\n{reason}',

    # --- settings
    'システムに合わせる': 'Follow system',
    'ダーク': 'Dark',
    'ライト': 'Light',
    '設定': 'Settings',
    '並び順を自動で決めるときに、次に使う番号。ほかのツールで作った武器と重なるときに変えてください。':
        'The next number used when the order is assigned automatically. Change it if it clashes with weapons made '
        'with other tools.',
    '言語': 'Language',
    '配色': 'Theme',
    '次に使う並び順の番号': 'Next order number',
    '言語の変更は、次に起動したときに反映されます。': 'The language change takes effect the next time the app starts.',
    'OS の言語に合わせる({name})': 'Follow the OS language ({name})',

    # --- stats page
    'すべてテンプレートの値に戻す': 'Reset all to template values',
    'テンプレートのまま': 'Same as template',
    '射撃動作の再生速度(weaponanimations.meta の AnimFireRateModifier)。1.0 が標準。小さいほど連射が遅く、大きいほど速くなる。空ならテンプレートの値のまま。':
        'Playback rate of the fire animation (AnimFireRateModifier in weaponanimations.meta). 1.0 is normal; lower fires slower, higher fires faster. Empty '
        'keeps the template value.',
    '項目名で絞り込み': 'Filter by field name',
    '性能': 'Stats',
    'テンプレートの値から変えたい項目だけ書き換えます。変えた項目は色が付きます。':
        'Change only the fields you want to differ from the template. Changed fields are highlighted.',
    '射撃動作の速度倍率': 'Fire animation rate',
    '主な項目': 'Main fields',
    '項目': 'Field',
    '値': 'Value',
    'テンプレートの値': 'Template value',
    'すべての項目': 'All fields',
    'テンプレートを読めません。': 'Cannot read the template.',

    # --- weapon page
    'モデル(.ydr)とテクスチャ(.ytd)の入ったフォルダ。ここへドロップしても選べます':
        'Folder containing the models (.ydr) and textures (.ytd). You can also drop it here',
    '読み直す': 'Rescan',
    'ゲーム内に表示される武器の名前。': 'The weapon name shown in game.',
    'スクリプトから武器を指す名前。WEAPON_ で始まる大文字の英数字。':
        'The name scripts use for the weapon. Upper-case, starting with WEAPON_.',
    '武器本体のモデル名(.ydr の拡張子なし)。': 'Model name of the weapon body (.ydr without the extension).',
    '書き出すリソースのフォルダ名。空なら武器 ID を小文字にしたものを使います。':
        'Folder name of the exported resource. Empty uses the weapon ID in lower case.',
    'この距離より遠いと武器モデルを描きません。': 'The weapon model is not drawn beyond this distance.',
    '表示名': 'Display name',
    '武器 ID': 'Weapon ID',
    'リソース名': 'Resource name',
    'モデルのフォルダを選ぶ': 'Select the model folder',
    '武器': 'Weapon',
    'モデルのフォルダを選び、元にするバニラ武器(テンプレート)と名前を決めます。':
        'Pick the model folder, then choose the vanilla weapon to base it on (the template) and its names.',
    'モデルのフォルダ': 'Model folder',
    'ファイル': 'File',
    '用途': 'Used for',
    '見つかったファイル': 'Files found',
    '基本': 'Basics',
    'テンプレートの変更': 'Change template',
    'テンプレートを変えると「性能」で変更した値は破棄されます。続けますか?':
        'Changing the template discards the values you changed under Stats. Continue?',
    'フォルダが選ばれていません。': 'No folder selected.',
    'このフォルダには .ydr / .ytd がありません。': 'This folder has no .ydr / .ytd files.',
    '{n} 個。チェックを外したファイルは書き出しません。': '{n} file(s). Unchecked files are not exported.',
    '武器本体': 'Weapon',
    '未割り当て': 'Unassigned',
    # --- template import
    '{files} 個の meta を読みました。武器 {w} 種、部品 {c} 種。': 'Read {files} meta files: {w} weapons, {c} components.',
    '{n} 個のテンプレートを取り込みました。': 'Imported {n} template(s).',
    'テンプレートを取り込む': 'Import templates',
    'meta の入ったフォルダ(サブフォルダも読みます)': 'Folder containing meta files (subfolders are read too)',
    'OpenIV / CodeWalker で書き出したバニラの meta や、アドオン武器のリソースのフォルダを選んでください。':
        'Select a folder with vanilla metas exported by OpenIV / CodeWalker, or an add-on weapon resource.',
    '名前で絞り込み': 'Filter by name',
    '新規だけ選ぶ': 'Select new only',
    '選択を外す': 'Clear selection',
    '取り込む': 'Import',
    '閉じる': 'Close',
    'meta の入ったフォルダを選ぶ': 'Select the folder with meta files',
    '状態': 'Status',
    '動作・構え方': 'Animations / movement',
    '部品': 'Component',
    'この中にある': 'Included',
    '推測': 'Guessed',
    '読めなかったファイル: {n} 個(XML でない meta など)': 'Unreadable files: {n} (e.g. metas that are not XML)',
    '新規': 'New',
    '取り込むと、こちらが優先して使われます。': 'If imported, this one takes precedence.',
    '取り込むものが選ばれていません。': 'Nothing is selected.',
    '{name} から借用': 'Borrowed from {name}',
    '無し(書き出し時に注意)': 'None (check before exporting)',
    '取り込み済み': 'Imported',
    '同梱にある': 'Bundled',
    '取り込めなかったもの:': 'Could not import:',
    'テンプレートを取り込む(&I)…': '&Import templates…',
    '取り込んだテンプレートのフォルダを開く': 'Open the imported templates folder',
    '取り込んだテンプレートです。': 'This is an imported template.',
    '動作と構え方は {names} のものを借りています。持ち方がバニラと違って見えることがあります。':
        'Animations and movement are borrowed from {names}. The way it is held may look different from vanilla.',
    # --- fire type / explosion / effects
    '発射方式が PROJECTILE ですが、弾薬 {ammo} は飛んでいく弾ではありません。ロケット等を撃たせるなら AMMO_RPG などを選んでください。':
        'The fire type is PROJECTILE, but ammo {ammo} is not a projectile. To fire rockets etc., choose AMMO_RPG or similar.',
    '発射方式 VOLUMETRIC_PARTICLE(噴射)と噴射用の弾薬(AMMO_FIREEXTINGUISHER など)は組み合わせて使います。今は {fire} と {ammo} です。':
        'The VOLUMETRIC_PARTICLE (spray) fire type and spray ammo (AMMO_FIREEXTINGUISHER etc.) go together. Currently {fire} and {ammo}.',
    '弾が飛ぶ武器ではないテンプレートから {ammo} を撃つと、弾が横向きのまま飛ぶことがあります(バニラのカービンのモデルで確認)。弾の向きはモデル側で決まるとみられ、ここの設定では直せません。':
        'Firing {ammo} from a template that is not a projectile weapon may make the projectile fly sideways (confirmed with the vanilla carbine model). The direction appears to come from the model and cannot be fixed here.',
    '着弾時の爆発 {explosion} を使うには、ダメージの種類を EXPLOSIVE にしてください(今は {damage})。そのままでは爆発しません。':
        'To use the impact explosion {explosion}, set the damage type to EXPLOSIVE (currently {damage}). It will not explode otherwise.',
    '弾薬 {ammo} はバニラでは PROJECTILE(弾が飛ぶ)の武器が使う弾です。発射方式が {fire} のままだと撃ち出されない可能性があります。撃ち出すなら発射方式を PROJECTILE にしてください。':
        'In vanilla, ammo {ammo} is used by PROJECTILE weapons. With the fire type left as {fire} it may not be fired as a projectile. Set the fire type to PROJECTILE to fire it.',
    '発射方式': 'Fire type',
    'INSTANT_HIT は弾が即座に当たる(普通の銃)。PROJECTILE は弾が実体として飛ぶ(ロケット・グレネード)。DELAYED_HIT はスナイパーライフル、VOLUMETRIC_PARTICLE は噴射(消火器・ガソリン缶)が使う方式。弾薬の種類と組み合わせて使います。':
        'INSTANT_HIT hits immediately (normal guns). PROJECTILE fires a physical projectile (rockets, grenades). DELAYED_HIT is used by sniper rifles and VOLUMETRIC_PARTICLE by sprays (fire extinguisher, jerry can). Use it together with the ammo type.',
    '着弾時の爆発': 'Explosion on impact',
    '弾が当たった所で起こす爆発。バニラの普通の銃は DONTCARE、レールガンは EXP_TAG_RAILGUN。ダメージの種類を EXPLOSIVE にしないと爆発しません。':
        'Explosion created where the shot hits. Normal vanilla guns use DONTCARE; the railgun uses EXP_TAG_RAILGUN. It only explodes when the damage type is EXPLOSIVE.',
    '発砲・噴射のエフェクト': 'Fire / spray effect',
    '撃ったときに出るエフェクトの名前。消火器では噴射の見た目にあたります。':
        'Name of the effect shown when firing. For the fire extinguisher this is the look of the spray.',
}
