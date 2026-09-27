$ErrorActionPreference = "Stop"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name VisionneuseAstro main.py
Write-Host "Executable created: dist\VisionneuseAstro.exe"
