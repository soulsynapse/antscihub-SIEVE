# FINDINGS

Measurements that shaped a design decision. Each entry says what was measured,
on what, and what changed because of it.

---

## Decode cost is colour conversion, not decoding

Measured 2026-07-25 on `videos-testing/stab_GX010050c2_02_18_26.MP4`
(5312x2988, H.264, 59.94 fps, 30 579 frames), OpenCV 4.13, Python 3.11.

| Operation | Cost |
|---|---|
| `VideoCapture(path)` + first `read()` | 213 ms |
| `grab()` (demux + decode, no colour convert) | 1.3 ms |
| `retrieve()` (YUV → BGR convert and copy) | 29 ms |
| Sequential `read()` (grab + retrieve) | 28.7 ms |
| Random `CAP_PROP_POS_FRAMES` seek + read | 80 ms |
| `resize` to 960 wide, `INTER_AREA` | 4.2 ms |

Almost all per-frame cost is the colour conversion. Two consequences:

1. **Short forward jumps grab rather than seek.** `VideoReader._position_at`
   grabs through gaps below `GRAB_FORWARD_LIMIT` (40 frames), which is
   strictly cheaper than a seek at ~1.3 ms/frame and avoids keyframe-rounding
   errors. Above that it seeks.
2. **Real-time playback is impossible for this footage** — 34 fps decode
   against a 59.94 fps source. `VideoPlayer` therefore drives from the wall
   clock and drops frames, so playback runs at correct *speed* at a lower
   frame rate. Verified: 2 s of playback advanced 117 source frames
   (58.5 src-fps, within 2.4% of real time) while rendering 36.5 fps.

## Scrub latency is met by coalescing, not by faster seeking

A single random seek costs ~80 ms against a 50 ms budget
(`scrub_to_repaint`), and no amount of tuning fixes that for 5.3K H.264 — the
seek alone is ~50 ms before any pixels are converted.

What is achievable, and what the budget is really about, is that the UI never
blocks and a scrub never falls behind the cursor. `VideoPlayer` keeps at most
one decode in flight and one pending, discarding everything in between.
Measured: a burst of 40 seeks settled on the final target in **172 ms** —
roughly two decodes, not forty. Queued, the same burst would have taken ~3.2 s
and shown 38 frames nobody asked for.

**Open question flagged rather than answered:** the single-seek number is
still a budget miss under the strict reading of non-negotiable #4. Options not
yet explored are a proxy/scrub-resolution decode pass, a keyframe-only scrub
mode while the slider is down, or a hardware decoder. This needs a decision
before the scrub budget can be asserted in `bench/` rather than described here.

## Open → first frame has headroom

213 ms against a 500 ms budget (`open_to_first_frame`), measured through the
full GUI path: `MainWindow.open_video` → decode thread → first repaint. The
container reports metadata in 25 ms; the remaining 188 ms is the first decode.
