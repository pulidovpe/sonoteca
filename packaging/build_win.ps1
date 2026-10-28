# Construye dist\musicapp\musicapp.exe y un .zip. Uso (PowerShell, en Windows): .\packaging\build_win.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[ui,build]"
pyinstaller packaging/musicapp.spec --noconfirm --clean

Write-Host "== Prueba de humo (5 s, sin pantalla) =="
$tmp = Join-Path $env:TEMP "sonoteca-smoke"
$env:MUSICAPP_SELFTEST = "1"; $env:QT_QPA_PLATFORM = "offscreen"; $env:QT_QUICK_BACKEND = "software"
$env:MUSICAPP_DATA_DIR = "$tmp\data"; $env:MUSICAPP_CACHE_DIR = "$tmp\cache"
$p = Start-Process -FilePath "dist\musicapp\musicapp.exe" -Wait -PassThru
if ($p.ExitCode -eq 0) { Write-Host "OK: la interfaz carga." } else { Write-Warning "FALLO: no arranca (codigo $($p.ExitCode)). Prueba con MUSICAPP_NO_PRUNE=1." }
Remove-Item Env:MUSICAPP_SELFTEST

$version = python -c "import musicapp; print(musicapp.__version__)"
"{0:N0} MB" -f ((Get-ChildItem dist\musicapp -Recurse | Measure-Object Length -Sum).Sum / 1MB)
Compress-Archive -Force -Path dist\musicapp -DestinationPath "dist\Sonoteca-$version-alpha-windows-x86_64.zip"
