# geometry

Draws circles, squares, rectangles and polygons over a video's frame and writes them as the geometry
file `tools/region.py` reads through its `geometry` path input, `load_geometry` being the live
statement of what that file may hold. Run it from the repo's root:

```
.venv\Scripts\python -m utilities.geometry --video PATH [--file PATH]
```

`--file` is opened when it is on disk and is otherwise where the first save lands. The file is region's
`plate` and `shapes` with a `drawing` key beside them, each shape's kind and stamp group, which region
ignores; a file without one, or written elsewhere, opens with each kind inferred from its shape.

Keep… saves the drawing to the library under a name, and every later run lists it with its plate and
date to load onto the open video. The library is Qt's per-user application data folder for
organization `SIEVE` and application `geometry`: `%APPDATA%\SIEVE\geometry` on Windows,
`~/Library/Application Support/SIEVE/geometry` on macOS, `~/.local/share/SIEVE/geometry` on Linux.
Each configuration is a geometry file there, `<name>.json`, and may be copied in or out by hand.

docs/spec/geometry.md is what it is to become; a deliverable whose boxes are ticked there is built.
