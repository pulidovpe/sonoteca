# Construye dist\sonoteca\sonoteca.exe y un .zip. Uso (PowerShell, en Windows): .\packaging\build_win.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
# Entorno propio de este script: se borra siempre (uno viejo o copiado de otra máquina falla)
if (Test-Path .venv-build) { Remove-Item -Recurse -Force .venv-build }
python -m venv --clear .venv-build
.\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[ui,build]"
pyinstaller packaging/sonoteca.spec --noconfirm --clean

Write-Host "== Prueba de humo (5 s, sin pantalla) =="
$tmp = Join-Path $env:TEMP "sonoteca-smoke"
$env:SONOTECA_SELFTEST = "1"; $env:QT_QPA_PLATFORM = "offscreen"; $env:QT_QUICK_BACKEND = "software"
$env:SONOTECA_DATA_DIR = "$tmp\data"; $env:SONOTECA_CACHE_DIR = "$tmp\cache"
$p = Start-Process -FilePath "dist\sonoteca\sonoteca.exe" -Wait -PassThru
if ($p.ExitCode -eq 0) { Write-Host "OK: la interfaz carga." } else { Write-Warning "FALLO: no arranca (codigo $($p.ExitCode)). Prueba con SONOTECA_NO_PRUNE=1." }
Remove-Item Env:SONOTECA_SELFTEST

python packaging/check_bundle.py dist\sonoteca
$version = python -c "import sonoteca; print(sonoteca.__version__)"
"{0:N0} MB" -f ((Get-ChildItem dist\sonoteca -Recurse | Measure-Object Length -Sum).Sum / 1MB)
Compress-Archive -Force -Path dist\sonoteca -DestinationPath "dist\Sonoteca-$version-alpha-windows-x86_64.zip"
