# リリースビルド: テスト → アイコン → PyInstaller → templates を exe の隣へ → zip
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..
$py = '.\.venv\Scripts\python.exe'
& $py -m unittest discover -s tests
if ($LASTEXITCODE -ne 0) { throw 'tests failed' }
if (-not (Test-Path assets\kn_weapontoolkit.ico)) { & $py scripts\make_icon.py }
& $py -m PyInstaller --noconfirm --clean kn_weapontoolkit.spec
if ($LASTEXITCODE -ne 0) { throw 'pyinstaller failed' }
# テンプレートは利用者が足せるよう、_internal ではなく exe の隣に置く
Copy-Item -Recurse -Force templates dist\kn_weapontoolkit\templates
Copy-Item -Force LICENSE, THIRD_PARTY_NOTICES.md, README.md, README.en.md dist\kn_weapontoolkit\
$ver = (& $py -c "import kn_weapontoolkit; print(kn_weapontoolkit.__version__)").Trim()
$zip = "dist\kn_weapontoolkit-$ver-win64.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path dist\kn_weapontoolkit -DestinationPath $zip
# build\ は PyInstaller の作業用(中の exe は単体では起動できない)なので残さない
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Write-Host "OK: $zip"
