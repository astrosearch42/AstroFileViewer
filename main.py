from __future__ import annotations

import json
import hashlib
import os
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
)
from PIL import Image, ImageOps

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".fits", ".tif", ".tiff", ".webp", ".gif", ".heic", ".heif", ".avif", ".mp4"}
DATE_PATTERN = re.compile(r"(?<!\d)(20\d{2})[-_](\d{2})[-_](\d{2})(?!\d)")
CATEGORY_LABELS = {
    "mak127": "Maksutov 127",
    "maksutov127": "Maksutov 127",
    "newton114": "Newton 114",
    "newton": "Newton 114",
    "landscape": "Landscape",
    "paysage": "Landscape",
    "montage photo": "Photomontage",
    "montage": "Photomontage",
}
CATEGORY_ORDER = {
    "Maksutov 127": 0,
    "Newton 114": 1,
    "Landscape": 2,
    "Photomontage": 3,
}
SOURCE_KEYS = ("Maksutov 127", "Newton 114", "Landscape", "Photomontage")
DEFAULT_SOURCE_KEYS = {"Maksutov 127"}

OBJECT_LABELS = {
    "Sun": "Sun",
    "Sol": "Sun",
    "Moon": "Moon",
    "Mercury": "Mercury",
    "Mercure": "Mercury",
    "Venus": "Venus",
    "Mars": "Mars",
    "Jup": "Jupiter",
    "Sat": "Saturn",
    "Saturn": "Saturn",
    "Uranus": "Uranus",
    "Neptune": "Neptune",
    "Pluto": "Pluto",
    "Pluton": "Pluto",
}

def human_size(size: int) -> str:
    value = float(size)
    for unit in ("o", "Ko", "Mo", "Go"):
        if value < 1024 or unit == "Go":
            return f"{value:.1f} {unit}" if unit != "o" else f"{int(value)} o"
        value /= 1024
    return f"{size} o"


def folder_date(path: Path) -> date | None:
    for part in reversed(path.parts):
        match = DATE_PATTERN.search(part)
        if match:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                return None
    return None


def category_label(path: Path, root: Path) -> str:
    relative_parts = path.relative_to(root).parts
    for part in relative_parts:
        key = part.casefold().replace("_", " ").strip()
        if key in CATEGORY_LABELS:
            return CATEGORY_LABELS[key]
    return relative_parts[0] if relative_parts else "Other"


@dataclass(frozen=True)
class AstroFile:
    path: Path
    category: str
    group: str
    object_name: str
    captured_on: date | None


class FileCard(QFrame):
    def __init__(self, path: Path, selected_callback, pixmap_cache: dict[Path, QPixmap] | None = None, parent=None):
        super().__init__(parent)
        self.path = path
        self.setFixedSize(202, 188)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setObjectName("fileCard")
        self.setProperty("selected", False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 7)
        layout.setSpacing(6)
        check_row = QHBoxLayout()
        check_row.addStretch()
        self.check = QCheckBox()
        self.check.setToolTip("Select this photo for export")
        self.check.stateChanged.connect(lambda: selected_callback(self))
        check_row.addWidget(self.check)
        layout.addLayout(check_row)
        self.preview = QLabel()
        self.preview.setFixedSize(184, 118)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setObjectName("preview")
        self.preview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.preview.customContextMenuRequested.connect(self._show_context_menu)
        if path.suffix.casefold() in IMAGE_EXTENSIONS:
            pixmap = (pixmap_cache or {}).get(path)
            if pixmap is None:
                pixmap = self._load_thumbnail(path)
                if pixmap_cache is not None and not pixmap.isNull():
                    pixmap_cache[path] = pixmap
            if not pixmap.isNull():
                self.preview.setPixmap(pixmap)
            else:
                self.preview.setText("Preview unavailable")
        else:
            self.preview.setText(path.suffix.upper().replace(".", "") or "FILE")
        layout.addWidget(self.preview)
        name = QLabel(self._short_name(path.name, 184))
        name.setToolTip(str(path))
        name.setObjectName("fileName")
        layout.addWidget(name)
        info = QLabel(human_size(path.stat().st_size))
        info.setObjectName("muted")
        layout.addWidget(info)
        self.preview.mouseDoubleClickEvent = lambda _event: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    @staticmethod
    def _short_name(name: str, width: int) -> str:
        metrics = QApplication.fontMetrics()
        return metrics.elidedText(name, Qt.TextElideMode.ElideMiddle, width)

    @staticmethod
    def _load_thumbnail(path: Path) -> QPixmap:
        try:
            source = path.stat()
            cache_key = hashlib.sha1(f"{path}|{source.st_mtime_ns}|{source.st_size}".encode("utf-8")).hexdigest()
            thumbnail_path = Path(tempfile.gettempdir()) / "FileViewer" / f"{cache_key}.jpg"
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            if not thumbnail_path.exists():
                with Image.open(path) as image:
                    image = ImageOps.exif_transpose(image)
                    image.thumbnail((184, 118), Image.Resampling.LANCZOS)
                    if image.mode not in ("RGB", "L"):
                        image = image.convert("RGB")
                    image.save(thumbnail_path, "JPEG", quality=88, optimize=True)
            pixmap = QPixmap()
            pixmap.load(str(thumbnail_path))
            return pixmap
        except (OSError, ValueError, Image.DecompressionBombError):
            return QPixmap()

    def _show_context_menu(self, position):
        menu = QMenu(self)
        menu.setTitle("Context Menu")
        open_folder = menu.addAction("Open folder containing the image")
        open_file = menu.addAction("Open the image")
        origin = self.sender() if isinstance(self.sender(), QWidget) else self
        action = menu.exec(origin.mapToGlobal(position))
        if action == open_folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path.parent)))
        elif action == open_file:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path)))

    def set_selected(self, selected: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class AstroView(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("FileViewer", "FileViewer")
        self.root: Path | None = None
        self.files: list[AstroFile] = []
        self.cards: list[FileCard] = []
        self.card_cache: dict[Path, FileCard] = {}
        self.pixmap_cache: dict[Path, QPixmap] = {}
        self.selected_objects: set[str] = set()
        self.selected_sources: set[str] = set(DEFAULT_SOURCE_KEYS)
        self.source_checks: dict[str, QCheckBox] = {}
        self.loading_dialog: QProgressDialog | None = None
        self.path_label = QLabel("No Astro folder selected")
        self.path_label.setObjectName("pathLabel")
        self.object_tree = QTreeWidget()
        self.object_tree.setHeaderHidden(True)
        self.object_tree.itemChanged.connect(self._object_changed)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Most recent to oldest", "Oldest to most recent"])
        self.sort_combo.currentIndexChanged.connect(self.refresh_files)
        self.gallery_widget = QWidget()
        self.gallery = QGridLayout(self.gallery_widget)
        self.gallery.setContentsMargins(14, 14, 14, 14)
        self.gallery.setSpacing(14)
        self.gallery_scroll = QScrollArea()
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.gallery_scroll.setWidget(self.gallery_widget)
        self.count_label = QLabel("0 file")
        self._build()
        saved_path = self.settings.value("astro/root", "")
        if saved_path and Path(saved_path).is_dir():
            self.load_folder(Path(saved_path))

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 28)
        header = QHBoxLayout()
        title = QLabel("Astronomy Workshop")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        choose = QPushButton("📁  Select the parent folder")
        choose.clicked.connect(self.choose_folder)
        header.addWidget(choose)
        outer.addLayout(header)
        outer.addWidget(QLabel("Select objects: their photos will be grouped by category and sorted by date of capture."))
        outer.addWidget(self.path_label)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        side = QFrame()
        side.setObjectName("sidePanel")
        side_layout = QVBoxLayout(side)
        source_title = QLabel("Source folders")
        source_title.setObjectName("sectionLabel")
        side_layout.addWidget(source_title)
        source_box = QFrame()
        source_layout = QVBoxLayout(source_box)
        source_layout.setContentsMargins(4, 4, 4, 8)
        for source in SOURCE_KEYS:
            check = QCheckBox(source)
            check.setChecked(source in DEFAULT_SOURCE_KEYS)
            check.toggled.connect(lambda checked, value=source: self._source_changed(value, checked))
            self.source_checks[source] = check
            source_layout.addWidget(check)
        side_layout.addWidget(source_box)
        object_title = QLabel("Objects to display")
        object_title.setObjectName("sectionLabel")
        side_layout.addWidget(object_title)
        side_layout.addWidget(self.object_tree, 1)
        clear = QPushButton("Reset objects")
        clear.clicked.connect(self.clear_objects)
        side_layout.addWidget(clear)
        splitter.addWidget(side)
        content = QFrame()
        content_layout = QVBoxLayout(content)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Sort by date:"))
        controls.addWidget(self.sort_combo)
        controls.addStretch()
        self.share_button = QPushButton("☍  Export selection as ZIP")
        self.share_button.clicked.connect(self.export_zip)
        controls.addWidget(self.share_button)
        content_layout.addLayout(controls)
        content_layout.addWidget(self.count_label)
        content_layout.addWidget(self.gallery_scroll, 1)
        splitter.addWidget(content)
        splitter.setSizes([250, 850])
        outer.addWidget(splitter, 1)

    def choose_folder(self):
        selected = QFileDialog.getExistingDirectory(self, "Select the parent Astro folder")
        if selected:
            self.load_folder(Path(selected))

    def load_folder(self, root: Path):
        self.loading_dialog = QProgressDialog("Scanning Astro folder...", None, 0, 0, self)
        self.loading_dialog.setWindowTitle("Please wait")
        self.loading_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.loading_dialog.setMinimumDuration(0)
        self.loading_dialog.setCancelButton(None)
        self.loading_dialog.show()
        self.setEnabled(False)
        QApplication.processEvents()
        self.root = root
        self.settings.setValue("astro/root", str(root))
        self.path_label.setText(str(root))
        self.files = []
        self.card_cache.clear()
        self.pixmap_cache.clear()
        for index, path in enumerate(root.rglob("*")):
            if not path.is_file() or path.suffix.casefold() not in IMAGE_EXTENSIONS:
                continue
            parts = path.relative_to(root).parts
            parsed = self._find_object_info(parts)
            if parsed is None:
                continue
            group, object_name = parsed
            self.files.append(AstroFile(path, category_label(path, root), group, object_name, folder_date(path)))
            if index % 20 == 0:
                QApplication.processEvents()
        self.selected_sources = set(DEFAULT_SOURCE_KEYS)
        for check in self.source_checks.values():
            check.blockSignals(True)
            check.setChecked(check.text() in DEFAULT_SOURCE_KEYS)
            check.blockSignals(False)
        self._rebuild_object_tree()
        self.selected_objects.clear()
        self.loading_dialog.setRange(0, len(self.files))
        self.loading_dialog.setValue(0)
        self.refresh_files()
        self.setEnabled(True)
        self.loading_dialog.close()
        self.loading_dialog.deleteLater()
        self.loading_dialog = None

    def _rebuild_object_tree(self):
        self.object_tree.blockSignals(True)
        self.object_tree.clear()
        groups: dict[str, dict[str, QTreeWidgetItem]] = {}
        visible_files = [item for item in self.files if item.category in self.selected_sources]
        for astro_file in visible_files:
            display_name = OBJECT_LABELS.get(astro_file.object_name, astro_file.object_name)
            groups.setdefault(astro_file.group, {})[astro_file.object_name] = QTreeWidgetItem([display_name])
        for group_name in sorted(groups, key=self._group_sort_key):
            group_item = QTreeWidgetItem([group_name])
            group_item.setFlags(group_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            group_item.setCheckState(0, Qt.CheckState.Unchecked)
            self.object_tree.addTopLevelItem(group_item)
            for object_name in sorted(groups[group_name], key=lambda value: value.casefold()):
                item = groups[group_name][object_name]
                item.setData(0, Qt.ItemDataRole.UserRole, object_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Unchecked)
                group_item.addChild(item)
            group_item.setExpanded(True)
        self.object_tree.blockSignals(False)

    def _source_changed(self, source: str, checked: bool):
        if checked:
            self.selected_sources.add(source)
        else:
            self.selected_sources.discard(source)
        visible_names = {item.object_name for item in self.files if item.category in self.selected_sources}
        self.selected_objects.intersection_update(visible_names)
        self._rebuild_object_tree()
        self.refresh_files()

    @staticmethod
    def _find_object_info(parts: tuple[str, ...]) -> tuple[str, str] | None:
        normalized_parts = [part.casefold().replace("é", "e") for part in parts]
        planet_index = next((index for index, part in enumerate(normalized_parts) if part in {"planetaire", "planeteres"}), None)
        if planet_index is not None:
            candidates = [part for part in parts[planet_index + 1:-1] if not DATE_PATTERN.search(part)]
            return ("Planetary", candidates[0]) if candidates else None

        deep_index = next((index for index, part in enumerate(normalized_parts) if part in {"ciel profond", "ciel-profond"}), None)
        if deep_index is not None:
            technical_groups = {"galaxies", "nebuleuses", "nebuleuses planetaires", "etoiles", "amas", "amas globulaires"}
            candidates = [part for part in parts[deep_index + 1:-1] if not DATE_PATTERN.search(part) and part.casefold().replace("é", "e") not in technical_groups]
            return ("Deep Sky", candidates[0]) if candidates else None

        source_names = {"mak127", "maksutov127", "newton114", "landscape", "paysage", "montage photo", "montage"}
        if normalized_parts and normalized_parts[0] in source_names:
            subfolders = [part for part in parts[1:-1] if not DATE_PATTERN.search(part)]
            return ("Other categories", subfolders[0] if subfolders else "Direct files")
        return None

    @staticmethod
    def _group_sort_key(value: str) -> tuple[int, str]:
        return ({"Planetary": 0, "Deep Sky": 1}.get(value, 2), value.casefold())

    def _object_changed(self, item: QTreeWidgetItem, _column: int):
        if item.parent() is None:
            self.object_tree.blockSignals(True)
            checked = item.checkState(0) == Qt.CheckState.Checked
            for index in range(item.childCount()):
                child = item.child(index)
                child.setCheckState(0, item.checkState(0))
                object_name = child.data(0, Qt.ItemDataRole.UserRole) or child.text(0)
                if checked:
                    self.selected_objects.add(object_name)
                else:
                    self.selected_objects.discard(object_name)
            self.object_tree.blockSignals(False)
        if item.parent() is not None:
            object_name = item.data(0, Qt.ItemDataRole.UserRole) or item.text(0)
            if item.checkState(0) == Qt.CheckState.Checked:
                self.selected_objects.add(object_name)
            else:
                self.selected_objects.discard(object_name)
        self.refresh_files()

    def clear_objects(self):
        self.selected_objects.clear()
        self.object_tree.blockSignals(True)
        for index in range(self.object_tree.topLevelItemCount()):
            group = self.object_tree.topLevelItem(index)
            group.setCheckState(0, Qt.CheckState.Unchecked)
            for child_index in range(group.childCount()):
                group.child(child_index).setCheckState(0, Qt.CheckState.Unchecked)
        self.object_tree.blockSignals(False)
        self.refresh_files()

    def refresh_files(self):
        while self.gallery.count():
            item = self.gallery.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self.cards.clear()
        if not self.root:
            self.count_label.setText("Select a parent Astro folder")
            return
        selected = [item for item in self.files if item.category in self.selected_sources and (not self.selected_objects or item.object_name in self.selected_objects)]
        descending = self.sort_combo.currentIndex() == 0
        categories: dict[str, list[AstroFile]] = {}
        for item in selected:
            categories.setdefault(item.category, []).append(item)
        row = 0
        columns = max(1, (self.gallery_scroll.viewport().width() - 28) // 216)
        for category in sorted(categories, key=lambda value: (CATEGORY_ORDER.get(value, 99), value.casefold())):
            category_label_widget = QLabel(category)
            category_label_widget.setObjectName("categoryLabel")
            self.gallery.addWidget(category_label_widget, row, 0, 1, columns)
            row += 1
            category_files = sorted(categories[category], key=lambda item: (item.captured_on or date.min, item.path.name.casefold()), reverse=descending)
            last_date: date | None = None
            column = 0
            for astro_file in category_files:
                if astro_file.captured_on != last_date:
                    if column:
                        row += 1
                        column = 0
                    date_label = QLabel((astro_file.captured_on or date.min).strftime("%d/%m/%Y") if astro_file.captured_on else "Date unknown")
                    date_label.setObjectName("dateSeparator")
                    self.gallery.addWidget(date_label, row, 0, 1, columns)
                    row += 1
                    last_date = astro_file.captured_on
                card = self.card_cache.get(astro_file.path)
                if card is None:
                    card = FileCard(astro_file.path, self._selection_changed, self.pixmap_cache)
                    self.card_cache[astro_file.path] = card
                card.setToolTip(f"{astro_file.object_name} · {astro_file.path}")
                self.cards.append(card)
                self.gallery.addWidget(card, row, column)
                if self.loading_dialog is not None:
                    self.loading_dialog.setValue(len(self.cards))
                    if len(self.cards) % 8 == 0:
                        QApplication.processEvents()
                column += 1
                if column == columns:
                    row += 1
                    column = 0
            if column:
                row += 1
        self.count_label.setText(f"{len(selected)} photo(s) displayed · {len(self.selected_objects)} object(s) selected")

    def _selection_changed(self, card: FileCard):
        card.set_selected(card.check.isChecked())

    def export_zip(self):
        selected_cards = [card for card in self.cards if card.check.isChecked()]
        cards = selected_cards or self.cards
        paths = [card.path for card in cards]
        if not paths:
            QMessageBox.information(self, "Export ZIP", "No photo to export.")
            return
        target, _ = QFileDialog.getSaveFileName(self, "Save ZIP", "selection-astro.zip", "ZIP Archives (*.zip)")
        if not target:
            return
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in paths:
                    archive.write(path, path.name)
            QMessageBox.information(self, "Export ZIP", f"{len(paths)} Photo(s) exported.")
        except OSError as error:
            QMessageBox.critical(self, "Export not possible", str(error))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Viewer")
        self.resize(1280, 820)
        self.setMinimumSize(940, 620)
        self.setCentralWidget(AstroView())


def apply_style(app: QApplication, dark: bool = True):
    style = """
        QWidget { font-family: 'Segoe UI'; font-size: 10pt; color: #202020; }
        QMainWindow, QWidget { background: #f7f7f7; }
        QTabWidget::pane { border: 0; background: #f7f7f7; }
        QTabBar::tab { padding: 12px 22px; color: #5f5f5f; border-bottom: 2px solid transparent; }
        QTabBar::tab:selected { color: #0b5cab; border-bottom: 2px solid #0b5cab; font-weight: 600; }
        QPushButton { background: #ffffff; border: 1px solid #d7d7d7; border-radius: 6px; padding: 9px 14px; }
        QPushButton:hover { background: #eef6ff; border-color: #0b5cab; }
        QPushButton:pressed { background: #dceeff; }
        QLabel#pageTitle { font-size: 22pt; font-weight: 650; color: #1b1b1b; }
        QLabel#pathLabel { color: #0b5cab; background: #edf5fc; border-radius: 5px; padding: 8px 10px; }
        QLabel#muted { color: #6d6d6d; font-size: 9pt; }
        QLabel#emptyState { color: #777777; font-size: 12pt; padding: 40px; }
        QScrollArea, QListWidget, QTreeWidget { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 7px; }
        QFrame#sidePanel { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 7px; }
        QFrame#fileCard { background: #ffffff; border: 1px solid #dedede; border-radius: 7px; }
        QFrame#fileCard[selected="true"] { border: 2px solid #0b5cab; background: #f1f8ff; }
        QLabel#preview { background: #f0f2f4; border-radius: 5px; color: #7a7a7a; }
        QLabel#fileName { font-weight: 600; }
        QLabel#sectionLabel { font-weight: 650; color: #202020; padding-top: 5px; }
        QLabel#categoryLabel { font-size: 12pt; font-weight: 650; color: #202020; padding: 10px 2px 4px; border-bottom: 1px solid #d8d8d8; }
        QLabel#dateSeparator { color: #0b5cab; font-weight: 600; padding: 8px 2px 2px; border-bottom: 1px solid #b9d7ef; }
        QListWidget::item { padding: 10px 8px; border-bottom: 1px solid #eeeeee; }
        QListWidget::item:selected { background: #e4f1ff; color: #202020; }
        QComboBox { background: #ffffff; border: 1px solid #d7d7d7; border-radius: 5px; padding: 8px; min-width: 180px; }
        QSplitter::handle { background: #e6e6e6; }
    """
    if dark:
        style += """
        QWidget, QMainWindow { background: #202020; color: #eeeeee; }
        QLabel#pageTitle, QLabel#categoryLabel { color: #ffffff; }
        QLabel#muted { color: #b9b9b9; }
        QLabel#pathLabel { color: #8bc8ff; background: #263b4d; }
        QLabel#dateSeparator { color: #8bc8ff; border-bottom-color: #315a78; }
        QFrame#sidePanel, QFrame#fileCard, QScrollArea, QTreeWidget { background: #292929; border-color: #454545; }
        QLabel#preview { background: #383838; color: #b9b9b9; }
        QTreeWidget, QScrollArea { color: #eeeeee; }
        QPushButton, QComboBox { background: #303030; color: #eeeeee; border-color: #555555; }
        QPushButton:hover { background: #263b4d; border-color: #6eb6ed; }
        QFrame#fileCard[selected="true"] { background: #263b4d; border-color: #6eb6ed; }
        """
    app.setStyleSheet(style)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FileViewer")
    apply_style(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
