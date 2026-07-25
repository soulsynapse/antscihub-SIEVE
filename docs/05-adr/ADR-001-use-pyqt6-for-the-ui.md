# ADR-001: Use PyQt6 for the user interface

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE needs a cross-platform desktop user interface for interactive video
inspection, parameter adjustment, overlays, plots, and long-running processing
workflows. The application is written in Python and uses OpenCV for video and
image processing.

PyQt6 provides mature Qt 6 desktop widgets, layouts, painting, signals and
slots, threading primitives, and platform integration from Python. OpenCV's
Python image data is represented by NumPy arrays, which can be presented in Qt
through `QImage` and `QPixmap` with explicit handling of array lifetime, row
stride, and OpenCV's BGR channel order. This keeps the UI and image-processing
layers in the same language and avoids a separate frontend runtime.

PyQt6 is dual-licensed under GPLv3 and a commercial Riverbank license. The free
distribution is appropriate only while SIEVE is distributed under GPLv3 or
another license compatible with PyQt6's GPLv3 terms. Merely making the source
public is not sufficient. At the time of this decision, the repository does
not contain a project license file, so that licensing gap must be resolved
before distribution.

## Decision

Use PyQt6 and Qt Widgets as the supported framework for SIEVE's desktop user
interface.

Keep OpenCV and NumPy in the processing layer. Adapt image buffers to Qt image
types at the GUI boundary rather than introducing Qt types into the core,
pipeline, or worker layers. Conversions must explicitly account for buffer
ownership, row stride, pixel format, and BGR-to-RGB ordering.

Distribute SIEVE under a GPLv3-compatible open-source license while using the
free PyQt6 distribution. If the project later requires GPL-incompatible or
proprietary distribution, obtain an appropriate commercial PyQt license or
supersede this ADR with a different UI framework decision.

## Alternatives considered

### Dear PyGui

Dear PyGui uses an immediate-mode interface and offers fast plotting, but it is
a weaker structural fit for SIEVE:

- It is less suited to complex, dockable, multi-panel layouts.
- It has no equivalent to `QGraphicsScene` for implementing a proper DAG
  editor.
- Generating widgets automatically from a Pydantic schema is more awkward.
- Its ecosystem is smaller for components such as node-graph editors and video
  widgets.

Dear PyGui would provide rendering performance that SIEVE does not need while
sacrificing the structural fit provided by PyQt6.

## Status

Accepted.

## Consequences

- SIEVE gets a mature, cross-platform desktop UI toolkit with native event
  handling, widgets, painting, signals and slots, and established Python
  bindings.
- NumPy/OpenCV frames can be displayed without a separate web or native
  frontend stack.
- Qt dependencies remain confined to the GUI and orchestration boundary;
  scientific processing and pipeline code remain usable headlessly.
- GUI updates must run on the Qt main thread. Expensive OpenCV or pipeline work
  must run outside that thread so the interface remains responsive.
- Image adapters need tests for channel order, non-contiguous arrays, row
  stride, and source-buffer lifetime. A `QImage` that references NumPy memory
  must not outlive that memory unless the image is copied.
- GUI tests should run headlessly with `QT_QPA_PLATFORM=offscreen`.
- Distribution using the free PyQt6 package imposes GPLv3 compatibility
  requirements. A commercial PyQt license is required if SIEVE is distributed
  under incompatible terms.
- The repository needs an explicit GPLv3-compatible project license; its
  current absence is unresolved by this ADR.

## References

- [Riverbank Computing: PyQt licensing](https://www.riverbankcomputing.com/software/pyqt)
- [Riverbank Computing: PyQt commercial licensing](https://riverbankcomputing.com/commercial/pyqt)
- [Qt documentation: QImage](https://doc.qt.io/qt-6/qimage.html)
- [OpenCV documentation: basic operations on images](https://docs.opencv.org/4.x/d3/df2/tutorial_py_basic_ops.html)
