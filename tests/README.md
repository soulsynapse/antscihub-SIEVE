# ADR tests

These are executable architectural experiments. They are not part of the
ordinary unit-test suite because they compare optional dependencies, GUI
integration, machine resources, and renderer behavior.

## Image viewer backends

`benchmark_image_viewers.py` compares:

- a Qt-native `QGraphicsView`/`QGraphicsPixmapItem` stack;
- a pyqtgraph `ViewBox`/`ImageItem` stack;
- an embedded napari `ViewerModel`/`QtViewer`.

Every backend runs in a fresh subprocess and receives the same deterministic
RGB frame plus composite and current-operation RGBA overlays. The harness
records frame-publication-to-draw latency, missed frame deadlines, dropped
presentations, CPU time, memory, initialization time, process startup time,
versions, logs, and screenshots.

Install the experiment dependencies into the repository virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r tests\requirements-image-viewers.txt
```

Run a short headless correctness smoke test:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe tests\benchmark_image_viewers.py `
    --offscreen --width 640 --height 360 --frames 12 --warmup-frames 3
```

On Windows, napari/VisPy currently requires a real OpenGL context and is
expected to fail under Qt's `offscreen` platform plugin. That failure is
recorded rather than hidden. Do not use offscreen timings to rank renderers.

Run the meaningful display/GPU comparison:

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe tests\benchmark_image_viewers.py `
    --width 1920 --height 1080 --fps 30 --frames 180 --warmup-frames 30
```

Results are written beneath `tests/results/`. Each run contains a combined
Markdown report, raw JSON per backend, worker logs, and screenshots.

### Interpretation limits

The three backends do not expose the same physical display-scan-out signal.
The harness records the closest backend-specific public draw-completion hook
and names that boundary in every result. Differences smaller than a few
milliseconds should not be treated as authoritative without a GPU capture.

This benchmark isolates frame presentation. It intentionally excludes video
decode, shared-memory transport, scientific processing, pipeline mutation, and
plot updates. Those need separate benchmarks before an end-to-end viewer
decision.
