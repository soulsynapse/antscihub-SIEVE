from __future__ import annotations

import sys


def main() -> int:
    try:
        from PyQt6.QtWidgets import QApplication
        from antscihub_sieve.gui.main_window import MainWindow
    except ImportError:
        print("sieve-gui requires PyQt6. Install it with: pip install 'antscihub-sieve[gui]'", file=sys.stderr)
        return 1
    application = QApplication(sys.argv); application.setApplicationName("SIEVE")
    window = MainWindow(); window.showMaximized()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
