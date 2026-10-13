$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$entryPoint = Join-Path $projectRoot "src\astrofileviewer\AstroFileViewer.py"
$iconPath = Join-Path $projectRoot "icon\afv.ico"
$svgPath = Join-Path $projectRoot "icon\afv.svg"

if (-not (Test-Path -LiteralPath $entryPoint -PathType Leaf)) {
    throw "Impossible de trouver le point d'entrée Python : $entryPoint"
}

if (-not (Test-Path -LiteralPath $iconPath -PathType Leaf)) {
    throw "Impossible de trouver l'icône : $iconPath"
}

if (-not (Test-Path -LiteralPath $svgPath -PathType Leaf)) {
    throw "Impossible de trouver l'icône SVG : $svgPath"
}

$resolvedEntryPoint = (Resolve-Path -LiteralPath $entryPoint).Path
$entryPointHash = (Get-FileHash -LiteralPath $resolvedEntryPoint -Algorithm SHA256).Hash
Write-Host "Point d'entrée Python : $resolvedEntryPoint"
Write-Host "SHA-256 du point d'entrée : $entryPointHash"

Push-Location $projectRoot
try {
uv run python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name AFV `
  --icon $iconPath `
  --add-data "$svgPath;icon" `
  $resolvedEntryPoint
}
finally {
    Pop-Location
}