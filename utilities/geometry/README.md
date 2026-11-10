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

docs/spec/geometry.md is what it is to become; a deliverable whose boxes are ticked there is built.
