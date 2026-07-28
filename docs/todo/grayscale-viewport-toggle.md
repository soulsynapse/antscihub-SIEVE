---
title: A grayscale viewport the user can reach from the viewport
status: open
opened: 2026-07-27
gated_on: >
  nothing — TAKE THIS FIRST, ahead of docs/todo/render-fed-playback.md, which is
  the second of the two and reads better once the pane can already go gray
reads:
  - src/sieve/gui/decode_worker.py
  - src/sieve/gui/player.py
  - src/sieve/gui/preferences.py
  - src/sieve/gui/video_view.py
---

# A grayscale viewport the user can reach from the viewport

Priority **1 of 2**. The other is docs/todo/render-fed-playback.md, and the
ordering is deliberate: this one is small, self-contained, and buys most of the
number; that one is the architectural half.

The pipeline decodes luma as of 2026.07.27
(docs/completed-todo/2026.07.27-grayscale-and-the-luma-decode.md). The viewport
does not — `gui/decode_worker.py:76` still reads full-resolution BGR and
downscales to a 1280-wide proxy, which is 22.7 ms a frame against the luma
path's 9.9.

From `docs/findings/2026.07.27-decode-is-a-bandwidth-wall-shared-by-two-consumers.md`,
same probe, reference footage:

```
                              alone            during a render
player colour            23.2 ms  43.1 fps    50.9 ms  19.6 fps
player luma               9.9 ms 100.8 fps    19.1 ms  52.3 fps
```

52.3 fps against 19.6 — the gray pane is 2.7x on the number the user actually
experiences, and it is the only configuration in that table above real time when
nothing else is running.

## The control belongs in the viewport, not in a dialog

Decided 2026-07-27, and it is the point of the item rather than a detail. A
preferences checkbox is where a setting goes to be found by someone who already
knows it exists. The person who needs this is watching a stuttering pane *right
now* and does not know that colour is what they are paying for — so the
affordance goes where the symptom is, on the viewport itself, and it says what
it buys.

Off by default. The pane is colour until the user says otherwise, because a
grayscale video pane is a surprise to everyone who did not ask for it, and the
analytical cost of colour is zero — the graphs are computed from luma either way.

**Decided 2026-07-27: reading (b).** "Off by default unless the render needs
it" parses as a condition, not a description — the pane drops to gray on its
own while a render is filling and returns to colour when it finishes. The
honesty requirement stands and is the toggle itself: while auto-gray is in
force, the viewport control shows it engaged with the reason in its label
("gray while rendering"), so the state is announced by the same affordance
that can override it, not by a separate badge. Clicking it during a render
pins colour and the automatic behaviour stands down for that render.
*Rejected side:* (a), purely manual — it leaves the default experience exactly
the stutter this item exists to fix, for every user who has not yet found the
toggle. *Falsifier:* if the pane changing appearance unbidden reads as a fault
in practice (the thing rule 6's mirror clause worries about), retreat to (a);
the manual toggle is unchanged either way. Build order stands: (a) first — it
is the whole mechanism — then (b) as the policy on top.

## Shape

**One flag, two consumers.** `DecodeWorker` opens its `VideoReader` with
`luma=`, exactly as `preview_runner` now does. The proxy stays 1280 wide and the
`GRAY2BGR` on the way out keeps `QImage` fed with BGR888, so `video_view.py` and
every overlay on it are untouched — 0.56 ms, measured, on the proxy rather than
the full frame.

**Reopening is the mechanism.** The format is fixed at capture construction
(`reader.py` says why it is never toggled mid-stream), so flipping the switch
closes and reopens the decode thread's reader. That is one capture, not
`PREVIEW_WORKERS` of them, and it happens on a deliberate click — but the
playhead must survive it and the pane must not blank, so the current frame is
re-requested at the new format rather than the viewport being cleared.

**`ProxyFrameCache` has to be dropped on the flip.** It is keyed by frame index
and says nothing about format, so a cache warmed in colour would hand colour
frames back after the switch — a viewport that is gray except where the user
happens to have scrubbed before. `player.py` already clears it on source change;
this is the second reason to.

**The preference persists** (`gui/preferences.py`, beside `adaptive_scrub` and
`proxy_width`, both of which are display decisions of exactly this kind), so the
toggle is a view over a stored value rather than a second place the answer lives.

## What to not get wrong

The label must say what it costs and what it buys, and both are short: colour
off, playback roughly 2.5x. A toggle labelled "grayscale" alone makes it look
like a viewing preference, which is the one thing it is not — nobody wants gray,
they want the frame rate.

This does not change what is computed. The graphs are derived from the luma plane
whatever the pane is showing, so the toggle must not appear anywhere near the
chain stack or read as a filter — rule 6's mirror clause, a control looking more
consequential than it is.
