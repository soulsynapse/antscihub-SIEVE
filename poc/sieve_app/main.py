"""SIEVE, one window: a folder of videos, the tools it found, and the player.

`uv run python poc/sieve_app/main.py [folder]`. Tools are discovered by path
under poc/tools/*/tool.py; the chain is the checked ones in list order, with
the series tool last. Nothing here imports a tool by name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

POC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POC))

from sieve_tool import Chain, PlayerWindow, VideoSource  # noqa: E402

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv"}


def discover_tools(root: Path) -> list[ModuleType]:
    found = []
    for path in sorted(root.glob("*/tool.py")):
        spec = importlib.util.spec_from_file_location(f"tools.{path.parent.name}.tool", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if all(hasattr(module, a) for a in ("NAME", "KIND", "DEFAULTS", "run", "settings")):
            found.append(module)
    return found


class SieveWindow(QMainWindow):
    def __init__(self, folder: Path) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE v0.4 proof of concept")
        self.tools = discover_tools(POC / "tools")
        self.player: PlayerWindow | None = None

        self.folder_label = QLabel()
        self.videos = QListWidget()
        self.videos.itemDoubleClicked.connect(self._open_video)
        open_button = QPushButton("Open folder…")
        open_button.clicked.connect(self._pick_folder)

        self.tool_list = QListWidget()
        self.tool_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        default_order = ["rescale", "normalize", "background ema", "block signal"]
        ordered = sorted(self.tools, key=lambda t: default_order.index(t.NAME) if t.NAME in default_order else 99)
        for tool in ordered:
            item = QListWidgetItem(f"{tool.NAME}  ({tool.KIND})")
            item.setData(Qt.ItemDataRole.UserRole, tool)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.tool_list.addItem(item)

        left = QVBoxLayout()
        left.addWidget(open_button)
        left.addWidget(self.folder_label)
        left.addWidget(QLabel("videos (double-click to open)"))
        left.addWidget(self.videos, 1)
        right = QVBoxLayout()
        right.addWidget(QLabel("tools found under poc/tools — check to include, drag to order"))
        right.addWidget(self.tool_list, 1)
        layout = QHBoxLayout()
        layout.addLayout(left, 1)
        layout.addLayout(right, 1)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.resize(700, 400)
        self._set_folder(folder)

    def _pick_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Folder of videos", str(self.folder))
        if chosen:
            self._set_folder(Path(chosen))

    def _set_folder(self, folder: Path) -> None:
        self.folder = folder
        self.folder_label.setText(str(folder))
        self.videos.clear()
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in VIDEO_SUFFIXES:
                self.videos.addItem(path.name)

    def _chain_tools(self) -> list[ModuleType]:
        chosen = []
        for i in range(self.tool_list.count()):
            item = self.tool_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                chosen.append(item.data(Qt.ItemDataRole.UserRole))
        return [t for t in chosen if t.KIND == "frame"] + [t for t in chosen if t.KIND == "series"]

    def _open_video(self, item: QListWidgetItem) -> None:
        if self.player is not None:
            self.player.close()
        source = VideoSource(self.folder / item.text())
        self.player = PlayerWindow(Chain(source, self._chain_tools()))
        self.player.show()


def main() -> int:
    app = QApplication(sys.argv)
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else POC.parent / "video-tests"
    window = SieveWindow(folder)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
