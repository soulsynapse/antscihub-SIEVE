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

The options left open here — proxy decode, keyframe-only scrubbing, hardware
decode — were measured and mostly closed. See the next entry.

## The seek is irreducible, so the budget is met by asking for less

Measured 2026-07-25 on the same source and build. The question was which of
the escape hatches from the previous entry actually exists.

| Probe | Result |
|---|---|
| `set(POS_FRAMES)` alone, random far target | **46.7 ms** median (min 29, max 202) |
| `grab()` after that seek | 0.4 ms |
| `retrieve()` (YUV → BGR) | 21.1 ms |
| Seek + grab + retrieve | 67.8 ms median, 226 ms worst |
| `CAP_PROP_CONVERT_RGB = 0` | 61.5 ms — saves ~6 ms, returns an unusable `8UC1` buffer |
| `VIDEO_ACCELERATION_ANY` | backend reports `HW_ACCELERATION = 0.0`; timing unchanged |

Two of the three hatches are shut. Hardware acceleration does not engage in
`opencv-python-headless`, and skipping the colour conversion buys 9% at the
cost of the frame. **The seek itself is ~70% of the cost and there is no knob
for it.**

Keyframe-only scrubbing was closed by a separate probe. Sweeping seek cost
across 150 consecutive targets should show a sawtooth if the cost were
av_seek-to-keyframe plus forward decode through the GOP — cheap on keyframes,
rising between them. There is no sawtooth: cost is 43–124 ms with no
periodicity at any offset. **Aligning a seek to a keyframe buys nothing here**,
so "keyframe seek" cannot be implemented as a cheaper seek. What it can be is
*fewer* seeks.

So the budget moved to 100 ms and is now met by degrading rather than by
decoding faster. `ScrubPolicy` watches the median of the last 5 scrub round
trips; above budget it snaps drag targets to a 1-second grid, and `FrameCache`
serves the repeats. The first pass over a region costs the same as before; the
grid is small and stable, so every later visit is a cache hit at no cost at
all — and a cache hit does not seek, which is the entire point. Releasing the
slider always decodes the exact frame, so coarse mode costs accuracy only
while the mouse is down.

The reference machine does *not* degrade on this clip: 68 ms median is inside
the 100 ms budget, which is the correct outcome and the reason the degradation
tests inject a policy with a threshold they can actually cross.

**Still open:** a sparse pre-decoded thumbnail track, which is what an NLE
actually does and what would make the *first* pass over a region cheap too.
Not built — it needs a place to put the thumbnails, which is the same decision
as where a project file lives.

## Open → first frame has headroom

213 ms against a 500 ms budget (`open_to_first_frame`), measured through the
full GUI path: `MainWindow.open_video` → decode thread → first repaint. The
container reports metadata in 25 ms; the remaining 188 ms is the first decode.
