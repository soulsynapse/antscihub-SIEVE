"""The app shell: one menu action, one panel (`ARCHITECTURE.md` 15.5).

[INTENT] "Default view is graphs, playback, and the replicate" is the eventual
shape; today there is only the video viewer, so the shell is that panel plus
File > Open. The other five regions in section 15 and the curated toolbar in
15.5 land with the panels they host.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from sieve.gui.panels.video_viewer import VideoViewer
from sieve.io.video_read import VideoReadError

_VIDEO_FILE_FILTER = "Video files (*.mp4 *.mov *.avi *.mkv);;All files (*)"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE")

        self._viewer = VideoViewer(self)
        self._viewer.scrubError.connect(self._on_scrub_error)
        self.setCentralWidget(self._viewer)
        self.statusBar()

        project_menu = self.menuBar().addMenu("&Project")
        open_action = project_menu.addAction("&Open Video…")
        open_action.triggered.connect(self._open_video_dialog)

    @property
    def viewer(self) -> VideoViewer:
        return self._viewer

    def _on_scrub_error(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)

    def _open_video_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Video", "", _VIDEO_FILE_FILTER)
        if not path:
            return
        self.open_video(path)

    def open_video(self, path: str) -> None:
        try:
            self._viewer.open(path)
        except VideoReadError as exc:
            QMessageBox.critical(self, "Could not open video", str(exc))
            return
        reduction = self._viewer.reader.info.describe_reduction() if self._viewer.reader else None
        if reduction:
            QMessageBox.information(self, "Bit depth reduced", reduction)
