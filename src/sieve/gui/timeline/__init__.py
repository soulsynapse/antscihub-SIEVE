"""The full-width band: where a frame lands on the strip, and what a click means.

Three modules — painting, arithmetic, and the window algebra — split for one
reason: every rule in `geometry.py` and `window.py` is wrong at the first or the
last frame before it is right anywhere, and a rule written inline in a
`paintEvent` is one whose failure is a band a few pixels off rather than a red
test.

The band reads the transport; the transport never reads it. That
one-directional edge is why `transport/` names nothing here.

**The working window is view state and not a document field.** v2 saved a span
on the project and narrowed a run with it; schema v1 narrows a run with a `span`
node in the graph (`adr/detector-is-a-node.md`), so what the bracket confines is
what the transport may reach — the stretch the user is watching — and nothing
here writes to the session.
"""
