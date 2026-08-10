---
title: One magnifier, and everything drawn on it maps to source pixels
step: "10.2"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'magnified or source_pixels_round_trip'"
opened: 2026-08-09
---

# One magnifier, and everything drawn on it maps to source pixels

The canvas can be zoomed and panned, and a region drawn while it is zoomed
lands on the source pixels the user aimed at. `gui/zoom.py` comes over from v2
whole — its argument is that two widgets in different units share one mapping
rule, which is v3's situation unchanged once the field overlay arrives — and
`video_view`'s fit rect, view rect and the two conversions come over with it.
`frame_rect()` stays as the name the existing geometry cases use.

This item is separate from 10.1 rather than a paragraph inside it because it is
the one place in the phase that can write a **wrong value into a saved
project**. `kind_editors.RegionEditor` reads `frame_rect()` today, which is the
fit; re-homed onto the view rect without the conversion, a box drawn at maximum
zoom lands in proxy or widget coordinates, produces a region that is wrong in
the document, and looks perfectly correct on screen. Nothing downstream would
catch it — the crop runs, the file is written, the numbers are simply not the
ones the user drew. Hence the round-trip as the criterion: the same region
drawn at the fit and drawn at maximum magnification resolves to the same source
pixels.

The rule that has to survive the port is v2's, and it is worth restating in the
module because it does not follow from the code: mapping goes to source pixels
and never through the proxy image, because the proxy's resolution changes with
a preference and between frames while what the document holds cannot.

## 2026-08-10 (review): what the port left behind

The mapping half is closed and independently re-verified — see the verdict on
the review commit. What the port did not bring over is the magnifier's
*lifecycle*: `reset_zoom()` landed with neither of v2's two callers, so a
magnification carries from one project's footage to the next. That is outside
this item's subject, which is where a drawn box resolves, and is
[a-magnification-is-a-view-of-this-footage.md](a-magnification-is-a-view-of-this-footage.md).

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui -q -k 'magnified or source_pixels_round_trip'
    181 deselected in 0.7s
    exit: 5
