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
- Python 3.15 or newer
- [uv](https://docs.astral.sh/uv/)

## Run from source

Install the dependencies declared in `pyproject.toml`, then run the application entry point:

```powershell
uv sync
uv run python src\astrofileviewer\AstroFileViewer.py
```

The application stores its settings under the `FileViewer/FileViewer` Windows application and organization names. The last selected folder is stored in the `astro/root` setting.

## Build the Windows executable

The build script resolves the project root from its own location, traces the Python source file and its SHA-256 hash, then invokes PyInstaller to create a windowed, one-file executable:

```powershell
.\scripts\build_exe.ps1
```

The generated executable is:

```text
dist\AFV.exe
```

The build uses the application icon at `icon\afv.ico` and includes `icon\afv.svg` for the window icon.

The application source is located at:

```text
src\astrofileviewer\AstroFileViewer.py
```

## Expected folder structure

The scanner recognizes these folder patterns:

```text
<parent folder>\Planetaire\<object>\<date>\image.jpg
<parent folder>\Ciel profond\<technical group>\<object>\<date>\image.jpg
<parent folder>\Maksutov 127\<object>\<date>\image.jpg
```

Dates are extracted from folder names containing `YYYY-MM-DD` or `YYYY_MM_DD`. Supported file extensions include `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.fits`, `.tif`, `.tiff`, `.webp`, `.heic`, `.heif`, `.avif`, and `.mp4`.
