# ADR-001: Use PySide6 for the user interface

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE needs a cross-platform desktop user interface for interactive video
inspection, parameter adjustment, overlays, plots, and long-running processing
workflows. The application is written in Python and uses OpenCV for video and
image processing.

PySide6 is the official Qt for Python binding. It provides mature Qt 6 desktop
widgets, layouts, painting, signals and slots, threading primitives, and
platform integration from Python. OpenCV's Python image data is represented by
NumPy arrays, which can be presented through Qt-compatible viewer and plotting
components. This keeps the UI and image-processing layers in the same language
and avoids a separate frontend runtime.

SIEVE's image and video surfaces require mature viewer chrome: pan and zoom,
layer ordering and visibility, opacity and blending, coordinate transforms,
contrast and colormap controls, and interactive points, shapes, labels, tracks,
and vectors. napari provides those facilities through a Qt viewer backed by
VisPy. SIEVE also requires intensive time-series and benchmark graphs;
pyqtgraph remains a better purpose-built component for those plot surfaces.

[STABLE] An executable comparison under `tests/benchmark_image_viewers.py` tested an
embedded napari viewer against pyqtgraph and Qt-native image stacks using the
same RGB frame and two RGBA overlays. Each candidate sustained 30 frames per
second without dropped presentations at 1920x1080 and 3840x2160. napari used
more memory and took approximately 2.2 seconds to initialize, but remained
within the preview frame budget and supplies substantially more required
viewer behavior.

The choice between the two principal Qt 6 Python bindings has a material
licensing consequence. The free PyQt6 distribution is GPLv3, not LGPL.
Riverbank states that software distributed under a license incompatible with
the GPL requires a commercial PyQt license. PySide6's Community Edition is
available under LGPLv3/GPLv3, as well as a separate Qt commercial license.
Using PySide6 under LGPLv3 therefore permits a wider range of application
licenses, subject to compliance with the LGPL and the licenses of the Qt
modules actually distributed.

## Decision

Use PySide6 and Qt Widgets as the supported framework for SIEVE's desktop user
interface.

Use an embedded napari `ViewerModel` and `QtViewer` for SIEVE's image and video
viewer surfaces. SIEVE remains the application shell: it owns playback, frame
and generation identity, timelines, pipeline state, operations, guidance,
benchmark reporting, and worker lifecycle. SIEVE is not implemented as a
napari plugin, and napari does not own the application event loop.

Use only napari's public APIs at the viewer boundary. napari layers are
presentation state and must not become the pipeline, filter, worker, CLI, or
serialized project data model.

Use pyqtgraph for intensive time-series plots, operation graphs, and benchmark
HUD surfaces. Selecting napari for image and video viewers does not replace
pyqtgraph where the product requires dense, rapidly updating graphs.

Keep OpenCV and NumPy in the processing layer. Adapt image buffers to napari or
pyqtgraph only at the GUI boundary rather than introducing their types into
the core, pipeline, or worker layers. Adapters must explicitly account for
buffer ownership, row stride, pixel format, OpenCV's BGR channel order, stable
display levels, and frame/generation identity.

Use the PySide6 Community Edition under LGPLv3 unless the project obtains an
appropriate commercial Qt license. Distribution must preserve the applicable
license notices and satisfy LGPLv3 requirements, including the user's ability
to replace or relink the LGPL-covered Qt libraries. Do not introduce
GPL-only Qt modules without a separate licensing decision.

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
sacrificing the structural fit provided by PySide6.

### PyQt6

PyQt6 has a comparable Qt API and mature tooling, but its free distribution is
licensed under GPLv3. Riverbank requires a commercial license when the
application's distribution terms are incompatible with the GPL. This would
either constrain SIEVE's application license to GPL-compatible terms or add a
commercial licensing dependency. PySide6 provides the required Qt 6 binding
under LGPLv3 and is therefore preferred.

### Qt-native or pyqtgraph image viewers

[STABLE] The executable viewer comparison showed that both alternatives can meet the
current raster-presentation frame budget. pyqtgraph had the lowest measured
draw-boundary latency and lower memory use than napari. Qt-native viewing had
the smallest dependency surface.

Neither alternative supplies napari's complete layer, annotation,
coordinate-transform, and display-control system. Using either as the primary
image viewer would make SIEVE responsible for substantially more viewer
chrome. pyqtgraph is retained for graphing, where its narrower and faster
plotting model is the desired behavior.

### Direct VisPy

[INTENT] Direct VisPy would retain GPU-backed rendering while avoiding napari's full
application and layer models. It would also require SIEVE to build the
higher-level layer controls, interaction modes, and coordinate behavior that
motivated the viewer-tool decision. Since embedded napari met the measured
preview budget, direct VisPy is not selected.

## Status

Accepted.

## Consequences

- SIEVE gets the official Qt 6 Python binding and a mature, cross-platform
  desktop UI toolkit with native event handling, widgets, painting, signals
  and slots.
- napari supplies the image/video canvas, layer model, pan/zoom, coordinate
  transforms, display controls, and annotation primitives.
- pyqtgraph supplies intensive time-series and benchmark plotting; the two
  tools have distinct responsibilities.
- NumPy/OpenCV frames and derived overlays can be displayed without a separate
  web or native frontend stack.
- Qt dependencies remain confined to the GUI and orchestration boundary;
  scientific processing and pipeline code remain usable headlessly.
- GUI updates must run on the Qt main thread. Expensive OpenCV or pipeline work
  must run outside that thread so the interface remains responsive.
- Viewer adapters need tests for channel order, non-contiguous arrays, row
  stride, source-buffer lifetime, frame/generation identity, stable display
  levels, and exact source-coordinate mapping.
- Ordinary Qt GUI tests should run headlessly with
  `QT_QPA_PLATFORM=offscreen`. On Windows, napari's VisPy canvas could not
  create an OpenGL context with Qt's offscreen platform plugin during the ADR
  test. Renderer tests therefore require a real or otherwise GL-capable test
  display; offscreen timings must not be treated as renderer measurements.
- The initial comparison ran against the live environment's PyQt6 binding.
  The selected napari integration must be validated with PySide6 before its
  first production use.
- napari adds startup time, memory use, an OpenGL requirement, and a
  substantially larger dependency graph than the lower-level alternatives.
- The viewer implementation must not import private `napari._*` modules or
  depend on undocumented napari child-widget structure.
- Existing PyQt6 imports, signal declarations, tests, packaging metadata, and
  documentation must be migrated and validated against PySide6.
- LGPLv3 is permissive about the surrounding application's license but still
  imposes distribution obligations. Packaging must retain notices, permit
  replacement or relinking of the covered libraries, and provide source for
  any modifications to those libraries as required by the LGPL.
- Each bundled Qt module and third-party component must be checked for its own
  license; this ADR does not assume every optional Qt module is LGPL-licensed.

## References

- [Riverbank Computing: PyQt License FAQ](https://www.riverbankcomputing.com/commercial/license-faq)
- [Riverbank Computing: PyQt commercial version](https://www.riverbankcomputing.com/commercial/pyqt)
- [Qt for Python documentation](https://doc.qt.io/qtforpython-6/)
- [Qt for Python: GNU Lesser General Public License](https://doc.qt.io/qtforpython-6/overviews/qtdoc-lgpl.html)
- [Qt for Python: third-party licenses](https://doc.qt.io/qtforpython-6/licenses.html)
- [Qt documentation: QImage](https://doc.qt.io/qt-6/qimage.html)
- [OpenCV documentation: basic operations on images](https://docs.opencv.org/4.x/d3/df2/tutorial_py_basic_ops.html)
- [napari `QtViewer` API](https://napari.org/stable/api/napari.qt.QtViewer.html)
- [napari layers](https://napari.org/stable/getting_started/layers.html)
- [pyqtgraph documentation](https://pyqtgraph.readthedocs.io/)
- [SIEVE image-viewer comparison harness](../../tests/benchmark_image_viewers.py)
