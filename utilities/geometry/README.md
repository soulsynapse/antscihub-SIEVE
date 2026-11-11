# geometry

Draws circles, squares, rectangles and polygons over a video's frame and writes them as the geometry
file `tools/region.py` reads through its `geometry` path input, `load_geometry` being the live
statement of what that file may hold. Run it from the repo's root:

```
.venv\Scripts\python -m utilities.geometry --video PATH [--file PATH]
```

`--file` is the file Save writes, opened when it is on disk; without it the file is
`<stem>-geometry.json` beside the first video opened, likewise opened when on disk. Save as and Open
alone move it. Save is the one thing that writes it, and writes nothing while the drawing is the
file's; a shape not edited since the file was read, and a top-level key the utility does not read,
are written back as the file had them. While the drawing differs from the file the title carries the
unsaved mark and the File panel says so, and closing, Open and loading a configuration ask Save,
Discard or Cancel first. The file is region's `plate` and `shapes` with a `drawing` key beside them,
each shape's kind and stamp group, which region ignores; a file without one, or written elsewhere,
opens with each kind inferred from its shape.

The Library panel's bookmark keeps the drawing under a name, and every later run lists it with its plate and
date to load onto the open video. The library is Qt's per-user application data folder for
organization `SIEVE` and application `geometry`: `%APPDATA%\SIEVE\geometry` on Windows,
`~/Library/Application Support/SIEVE/geometry` on macOS, `~/.local/share/SIEVE/geometry` on Linux.
Each configuration is a geometry file there, `<name>.json`, and may be copied in or out by hand.

docs/spec/geometry.md is what it is to become; a deliverable whose boxes are ticked there is built.
