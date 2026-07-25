"""The Qt application: the only layer permitted to import a GUI toolkit.

Reaches ``workers`` only through ``pipeline``. The QObject adapter over the
metric bus lives here rather than in ``bench``, so that headless and CLI runs
can observe without Qt.
"""
