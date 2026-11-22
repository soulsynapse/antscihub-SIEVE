# A bare walk of the whole camera file dies of an access violation, and so does Python alone

2026-11-21, on `v5-playground-one-store` and on `v5` at `b23ff2c4`. The machine: Alienware Aurora
R16, Intel Core i9-14900KF, BIOS 2.25.0, 64 GiB, Windows 11. The player's Python 3.13.5, numpy
2.5.4, cv2 5.0.0.

## The walk

`docs/findings/experiments/bare_walk_thrice.py video-tests/purb-168-178.json video-tests/00000.MTS <folder>`:
the crossings clip's document (video, threshold, blobs, then track, travel, size, count) walked
bare over all 38100 rows of the file it was cut from, each walk its own process.

| tree | document | ended | died at | exit | the fault handler's line |
|---|---|---|---|---|---|
| playground, rows kept | whole | no | about 51 s | 0xC0000005 | not taken |
| playground, rows kept | whole | no | about 45 s | 0xC0000005 | not taken |
| playground, rows kept | whole | no | about 10 s | 0xC000001D | not taken |
| playground, none kept | whole | no | row 22607 | 0xC0000005 | `tools/track.py:80` |
| playground, none kept | whole | no | about 16 s | 0xC0000005 | `tools/track.py`, in `step` |
| playground, none kept | whole | no | row 12990, 52 s | 0xC0000005 | `tools/track.py`, in `step` |
| `v5` | whole | no | row 13855 | 0xC0000005 | `tools/track.py:80` |
| playground, none kept | less track and travel | yes, 115 s | | 0 | |

The process held 0.47 GiB of working set and 1.19 GiB committed when it died at 52 s: memory had
not run out. The same whole document over the ten-second clip ends every time, six walks of six.

## Python alone

The lines of `track.py` the handler named make a list of tuples of numpy scalars and sort it.
Loops that do only that, with nothing of SIEVE imported, die the same way within a minute, some
runs and not others:

| interpreter | numpy | loop | runs | died |
|---|---|---|---|---|
| 3.13.5 | 2.5.4 | tuples of `p[j]` from an array, sorted | 2 | 2 |
| 3.13.5 | 2.5.4 | `[a[k] for k in range(25)]` | 1 | 1 |
| 3.13.5 | 2.5.4 | `list(np.arange(25))` | 4 | 2 |
| 3.13.5 | 2.5.4 | `a.tolist()`, `np.float64(0.5)`, `rng.random`, `np.flatnonzero` alone | 1 each | 0 |
| 3.13.5 | 2.2.6 | `list(np.arange(25))` | 4 | 1 |
| 3.12.3 | 2.2.6 | `list(np.arange(25))`, `[a[k] ...]` | 2 each | 1 each |
| 3.13.5 | none imported | tuples of Python floats and ints from a list or an `array.array`, sorted | 4 | 1 |

The last row has no numpy in it. Two interpreters and two numpys die alike.

## The machine's own log

Windows' WHEA-Logger holds three events 19, "A corrected hardware error has occurred. Reported by
component: Processor Core. Error Source: Corrected Machine Check. Error Type: Internal parity
error. Processor APIC ID: 24": one on 2026-11-12 and two on 2026-11-21 at 18:52 and 18:54, inside
the hour these loops were run.

## What it shows and does not

- The fault is not SIEVE's, not this branch's, and not one numpy's: plain Python dies of it.
- It is not memory run out.
- `track` is where a walk meets it because `track` is the walk's one place that makes and sorts
  thousands of small Python objects a row; without it the walk ended, once of one.
- A processor core reporting corrected parity errors while short allocation-heavy loops die of
  access violations at places that move is what an unstable processor looks like, and this
  model is one Intel has acknowledged an instability in. That this machine has it is an
  inference from those two things together, not a diagnosis: no memory test was run, no core
  was taken out of use to see the faults stop, and the BIOS's microcode was not read.
- Until it is settled, a result this machine computed is under the same doubt as the walks that
  died: a core that faults loudly some of the time may also compute wrongly without faulting.

## What would settle it

The loops above pinned to cores other than the one of APIC ID 24, and then to it alone; a memory
test; the same loops on another machine; the BIOS and microcode against Dell's and Intel's
current ones for this processor.
