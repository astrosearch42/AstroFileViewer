# AstroFileViewer

AstroFileViewer is a Windows desktop application built with PySide6. It scans an astronomy folder, detects astronomical objects from the folder structure, and displays the matching files in a date-sorted gallery.

## Features

- Select and scan a parent Astro folder recursively.
- Detect planetary and deep-sky objects from the folder hierarchy.
- Filter files by source folder: `Maksutov 127`, `Newton 114`, `Landscape`, or `Photomontage`.
- Select individual objects or complete object groups.
- Sort files from newest to oldest or from oldest to newest.
- Preview supported image files and open them with the default Windows application.
- Export the selected files, or all displayed files when nothing is selected, to a ZIP archive.
- Remember the last selected folder through Windows `QSettings`.

## Requirements

- Windows
- Python 3.10 or newer
- PySide6
- Pillow

## Run from source

Create and activate a virtual environment, install the dependencies, then run the actual application entry point:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python AstroFileViewer.py
```

The application stores its settings under the `FileViewer/FileViewer` Windows application and organization names. The last selected folder is stored in the `astro/root` setting.

## Build the Windows executable

`build_exe.ps1` invokes PyInstaller with the project entry point and creates a windowed, one-file executable:

```powershell
.\build_exe.ps1
```

The generated executable is:

```text
dist\AFV.exe
```

The build uses the application icon at `icon\afv.ico` and includes `icon\afv.svg` for the window icon.

## Expected folder structure

The scanner recognizes these folder patterns:

```text
<parent folder>\Planetaire\<object>\<date>\image.jpg
<parent folder>\Ciel profond\<technical group>\<object>\<date>\image.jpg
<parent folder>\Maksutov 127\<object>\<date>\image.jpg
```

Dates are extracted from folder names containing `YYYY-MM-DD` or `YYYY_MM_DD`. Supported file extensions include `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.fits`, `.tif`, `.tiff`, `.webp`, `.heic`, `.heif`, `.avif`, and `.mp4`.
