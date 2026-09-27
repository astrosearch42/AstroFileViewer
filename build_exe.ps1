python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name AFV `
  --icon icon\afv.ico `
  --add-data "icon\afv.svg;icon" `
  AstroFileViewer.py