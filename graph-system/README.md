# graph-system

Regenerate the data: `uv run python graph-system/extract.py`
Open `graph-system/viewer.html` in a browser — no server, no build step.

Pick a scope in the tree or by double-clicking a node. Three views per scope:
**Internals** (the children, individually), **Interior** (edges among the
children only, outside collapsed to terminals), **Boundary** (the scope versus
everything upstream and downstream, with depth dials). Amber edges are the
`.importlinter` grandfathered exceptions; red would be an edge going up the
layer order. View state lives in the URL hash, so any view is bookmarkable.
