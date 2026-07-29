# GUI mockups

Runnable layout sketches, for deciding what a panel looks like *before* it is
built into `src/sieve/gui/`.

## Why these are PySide6 and not drawings

A mockup in HTML, Figma, or ASCII can propose a layout Qt cannot produce, and
the discrepancy is only discovered after the widget is written. These use the
real toolkit, the real splitters, the real font metrics, and — where it costs
nothing — the real widgets: `mockups/filter_tab.py` puts a genuine
`gui/video_view.VideoView` and a genuine `gui/timeline_bar.TimelineStrip` on
screen. What you see is what the layout will actually do when a window is
resized.

## What they are not

Not production code, not part of the package, and not imported by anything
under `src/`. `pyright` does not see this directory because its configured
include path is only `src`.

They are also **not promoted into `src/` by copying.** A mockup is fake data in
a hurry; the widget that replaces it is written against real signals with real
production contracts. What survives is the layout decision, recorded in the
TODO item or the completed entry that cites the mockup.

## Running one

```
uv run python mockups/filter_tab.py --variant a
uv run python mockups/filter_tab.py --variant b
```

To render a PNG instead of opening a window — which is how these get reviewed
without a display:

```
uv run python mockups/filter_tab.py --variant a --png out.png
```

Footage: a mockup that can find `videos-testing/` uses a real frame, because a
synthetic gradient makes every layout look fine. Without it, it falls back to a
generated frame and says so on screen.

## Convention

One file per panel under discussion, named for the thing it mocks. Variants
live in the same file behind `--variant`, so the differences are diffable
rather than scattered across near-identical copies. Delete a file once the real
widget lands and the decision is written down somewhere durable.
