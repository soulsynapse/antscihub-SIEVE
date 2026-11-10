"""`python -m utilities.geometry [--video PATH]`, run from the repo's root or with it on the path."""
import argparse
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .window import GeometryWindow, styled


def parser():
    p = argparse.ArgumentParser(prog="python -m utilities.geometry",
                                description="Draw shapes over a video's frame for the geometry file a region reads.")
    p.add_argument("--video", help="the video to draw over; asked for when absent")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    styled(app)
    win = GeometryWindow(args.video)
    win.show()
    if args.video is None:
        QTimer.singleShot(0, win.ask_video)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
