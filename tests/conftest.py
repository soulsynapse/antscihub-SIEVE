from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_qsettings(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from PyQt6.QtCore import QSettings
    from antscihub_sieve.gui import main_window
    settings = QSettings(str(tmp_path / "sieve-test.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(main_window, "default_settings", lambda: settings)


@pytest.fixture
def video(tmp_path: Path) -> Path:
    path = tmp_path / "parent.mkv"
    completed = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
        "testsrc2=size=18x14:rate=6:duration=2", "-c:v", "ffv1", "-pix_fmt", "bgr0", str(path)], capture_output=True)
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    return path
