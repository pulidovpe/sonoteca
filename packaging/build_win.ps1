# Construye dist\musicapp\musicapp.exe y un .zip. Uso (PowerShell): .\packaging\build_win.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[ui,build]"
pyinstaller packaging/musicapp.spec --noconfirm --clean
$version = python -c "import musicapp; print(musicapp.__version__)"
Compress-Archive -Force -Path dist\musicapp -DestinationPath "dist\musicapp-$version-alpha-windows-x86_64.zip"
