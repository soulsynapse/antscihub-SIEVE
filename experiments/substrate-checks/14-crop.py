"""Is every crop this can produce a legal one, and does it stop moving?

T0 of `docs/tuning/plan.md`. A crop is four integers in source pixels and three
rules hold of every one that leaves `sieve.analysis.crop`: it is on the frame,
it is at least `MINIMUM` on a side, and every edge is even.

**The third is the one that is not obvious.** 4:2:0 stores chroma at half
resolution in each direction, so an odd offset or an odd width puts a crop's
edge in the middle of a chroma sample; the encoder rounds it and a stored chunk
comes back a pixel adrift from the frame it was cut from. The explorers snap to
even with the comment `yuv420 wants even` and this is that rule with a check
under it.

**And the three interact, which is the whole difficulty.** Snapping a width down
to even after clamping it to a minimum can put it back under the minimum;
clamping an offset after snapping it can make it odd again; snapping *up* can
push an edge past the frame it has just been clamped onto. Each produces
something that looks clamped and is not, and nothing downstream would report it
— a crop a pixel off the frame is a form whose key names pixels the source does
not have.

**Two properties catch different halves of that, and both are needed.**
Legality catches a rule applied in the wrong *direction*: an edge that ends up
off the frame is off it however tidily it got there. Idempotence catches a rule
applied in the wrong *order*: `clamp(clamp(r)) == clamp(r)` fails the moment one
rule undoes another, and a clamp that moves a value it has already approved is
one whose editor will oscillate — push, corrected, push, corrected. Neither
implies the other, and an earlier draft of this file assumed idempotence would
catch everything and had to be told otherwise by a run.

Six cases, no footage and no Qt: a rectangle is arithmetic.

**legal** — every result of every clamp is on the frame, big enough and even,
over a sweep of awkward rectangles: negative, backwards, enormous, one pixel,
straddling every edge and corner. On frames a recording actually has, which is
the other half of the property: a clamp only has to be right about inputs that
can reach it.

**idempotent** — clamping twice is clamping once, over the same sweep.

**untouched** — a rect that is already legal comes back exactly as it went in.
A clamp that nudged its own approved output would make a typed number
unenterable.

**mapping** — a rectangle drawn over a placed picture round-trips to source
pixels and back, including through a stage whose aspect differs from the
source's, and a drag made backwards is the same crop as the same drag made
forwards.

**whole** — the whole frame is a legal crop of itself.

`--broken` snaps to the *nearest* even number rather than down to it, which is
the one thing `crop._even`'s own docstring says it does not do. `legal` and
`cramped` fail: an edge rounded up lands past the frame it was just clamped
onto. `idempotent` passes, because rounding an even number to the nearest even
number is the number — which is why legality is checked separately and not
assumed to follow.

The first version of this `--broken` clamped before snapping instead, and it
turned out to be *fine* on any frame larger than the floor: it only misbehaved
on frames narrower than sixty-four pixels, which no recording is. It was
replaced rather than kept, because a broken mode that only fails on inputs the
application never sees demonstrates nothing about the application.

Run:
    uv run --group experiments python experiments/substrate-checks/14-crop.py
    uv run --group experiments python experiments/substrate-checks/14-crop.py --broken
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.analysis import crop as crop_mod  # noqa: E402
from sieve.analysis.crop import MINIMUM, to_placed, to_source, whole  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

#: Frames a recording actually has: the 5.3K and the small clip in
#: `video-tests/`, plus an odd-sided one so the even-alignment has something to
#: do. A one-pixel frame was in this list, and it was the only place a whole
#: branch of `crop.clamp` was ever exercised — a check that invents an input
#: keeps alive the code that answers it.
FRAMES = ((5312, 2988), (462, 456), (1921, 1081), (640, 481))
SEED = 20260824


def nearest_even(value: int) -> int:
    """To the *nearest* even number rather than down to it.

    Kept here as the thing being argued against, and it is what
    `crop._even` says it is not: "Down and never nearest. Rounding to nearest
    would sometimes round up, and up is the direction that can push an edge off
    the frame after it has already been clamped onto it." This is that claim
    with a check under it — a rule whose reasoning is written down and never
    exercised is a rule nobody has tested, and the down-ness reads like
    fastidiousness until an edge lands past the last row of pixels.
    """
    return int(round(value / 2)) * 2


def illegal(rect, frame_width, frame_height, minimum=MINIMUM) -> str | None:
    """Why this crop is not one, or `None`.

    Area is checked first and unconditionally. A first version wrote the floor
    as `min(minimum, _even(frame))`, which on a one-pixel frame is zero — so a
    zero-area crop, the exact thing the floor exists to prevent, passed through
    a hole in the thing looking for it.
    """
    x, y, width, height = rect
    if any(v % 2 for v in rect):
        return f"{rect} has an odd edge"
    if width < 2 or height < 2:
        return f"{rect} has no area"
    if width < min(minimum, _even(frame_width)) or \
            height < min(minimum, _even(frame_height)):
        return f"{rect} is under the {minimum}px floor"
    if x < 0 or y < 0:
        return f"{rect} starts off the frame"
    if x + width > frame_width or y + height > frame_height:
        return f"{rect} runs past {frame_width}x{frame_height}"
    return None


def _even(value: int) -> int:
    return value - value % 2


def awkward(frame_width: int, frame_height: int):
    """Rectangles chosen to sit on every seam the three rules make."""
    w, h = frame_width, frame_height
    return [
        (0, 0, w, h),                       # the whole frame
        (0, 0, 1, 1),                       # nothing
        (-500, -500, 100, 100),             # off the top left
        (w - 3, h - 3, 500, 500),           # off the bottom right
        (w // 2, h // 2, -200, -200),       # drawn backwards
        (1, 1, MINIMUM - 1, MINIMUM - 1),   # a pixel under the floor, odd
        (1, 1, MINIMUM + 1, MINIMUM + 1),   # a pixel over it, odd
        (w - MINIMUM - 1, h - MINIMUM - 1, MINIMUM + 5, MINIMUM + 5),
        (3, 5, w, h),                       # offset, full size: must shrink
        (0, 0, w * 4, h * 4),               # far larger than the frame
    ]


def case_legal(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    checked = 0
    rng = random.Random(SEED)
    for width, height in FRAMES:
        rects = awkward(width, height) + [
            (rng.randint(-width, width * 2), rng.randint(-height, height * 2),
             rng.randint(-width, width * 2), rng.randint(-height, height * 2))
            for _ in range(400)
        ]
        for rect in rects:
            got = crop_mod.clamp(rect, width, height)
            checked += 1
            why = illegal(got, width, height)
            if why:
                bad.append(f"{width}x{height}: {rect} clamped to {why}")
                if len(bad) >= 6:
                    return "legal (on, big enough, even)", checked, bad
    run.note(f"legal: {checked} rectangles over {len(FRAMES)} frame sizes, "
             "every result on the frame, at least the floor, and even")
    return "legal (on, big enough, even)", checked, bad


def case_idempotent(run: Run) -> tuple[str, int, list[str]]:
    """The assertion that catches every ordering mistake at once."""
    bad: list[str] = []
    checked = 0
    rng = random.Random(SEED + 1)
    for width, height in FRAMES:
        rects = awkward(width, height) + [
            (rng.randint(-width, width * 2), rng.randint(-height, height * 2),
             rng.randint(1, width * 2), rng.randint(1, height * 2))
            for _ in range(400)
        ]
        for rect in rects:
            once = crop_mod.clamp(rect, width, height)
            twice = crop_mod.clamp(once, width, height)
            checked += 1
            if once != twice:
                bad.append(f"{width}x{height}: {rect} -> {once} -> {twice}; "
                           "a clamp that moves its own output makes a field "
                           "that shows it oscillate")
                if len(bad) >= 6:
                    return "idempotent (clamping twice is once)", checked, bad
    run.note(f"idempotent: {checked} rectangles, clamping twice never differed "
             "from clamping once")
    return "idempotent (clamping twice is once)", checked, bad


def case_untouched(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    legal = [
        (0, 0, 64, 64),
        (2144, 982, 1024, 1024),        # the rect both explorers hardcode
        (0, 0, 5312, 2988),
        (100, 200, 300, 400),
    ]
    for rect in legal:
        got = crop_mod.clamp(rect, 5312, 2988)
        if got != rect:
            bad.append(f"a legal {rect} was moved to {got}")
    run.note("untouched: a crop that is already legal is returned as it was, "
             "so a typed number can be entered at all")
    return "untouched (legal in, same out)", len(legal), bad


def case_mapping(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    source = (5312, 2988)
    # a stage whose aspect differs from the source's, which is what a pane
    # dragged narrow actually gives
    for placed in ((0, 0, 800, 450), (37, 11, 640, 640), (5, 5, 200, 90)):
        rect = to_source((placed[0] + 100, placed[1] + 50, 200, 120), placed,
                         *source)
        why = illegal(rect, *source)
        if why:
            bad.append(f"placed {placed}: {why}")
            continue
        back = to_placed(rect, placed, *source)
        again = to_source(back, placed, *source)
        if again != rect:
            bad.append(f"placed {placed}: {rect} -> {back} -> {again}")

    # a drag made backwards is the same crop as the same drag made forwards
    placed = (0, 0, 800, 450)
    forwards = to_source((100, 100, 200, 150), placed, *source)
    backwards = to_source((300, 250, -200, -150), placed, *source)
    if forwards != backwards:
        bad.append(f"a backwards drag gave {backwards} where forwards gave "
                   f"{forwards}")

    # a stage with no area is not an error, it is a picture nobody has placed
    if illegal(to_source((0, 0, 10, 10), (0, 0, 0, 0), *source), *source):
        bad.append("an unplaced picture produced an illegal crop")
    run.note("mapping: a drawn rect round-trips through stages of three "
             "different aspects, and direction of drag does not reach the crop")
    return "mapping (through the placed rect)", 5, bad


def case_whole(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    for width, height in FRAMES:
        rect = whole(width, height)
        why = illegal(rect, width, height)
        if why:
            bad.append(f"{width}x{height}: whole frame is {why}")
        # Stated here rather than asked of `frame.form.grade`, which is where
        # containment lives for `src/`. Deleting the duplicate *from the module*
        # was right; importing the real one *into the check* was an
        # over-correction — a check that runs the code under test agrees with
        # it by construction, and would go on agreeing if that code were wrong.
        # A restatement in a check is not the duplication that hurts.
        ix, iy, iw, ih = crop_mod.clamp((10, 10, 40, 40), width, height)
        ox, oy, ow, oh = rect
        if not (ox <= ix and oy <= iy
                and ix + iw <= ox + ow and iy + ih <= oy + oh):
            bad.append(f"{width}x{height}: the whole frame does not contain a "
                       "crop of it")
    run.note("whole: the whole frame is a legal crop of itself on every frame "
             "size, including the odd ones")
    return "whole (of itself)", len(FRAMES), bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        crop_mod._even = nearest_even

    run = Run(
        experiment="T0-crop" + ("-broken" if broken else ""),
        question="Is every crop this produces on the frame, big enough and "
                 "even — and does clamping one twice differ from once?",
    )
    run.note("no footage and no Qt: a rectangle is arithmetic")
    if broken:
        run.note("RUN WITH --broken: the clamp snaps to even *after* applying "
                 "the floor, which reads correctly and undoes the floor. "
                 "`legal` and `idempotent` are expected to FAIL.")

    results = [
        case_legal(run),
        case_idempotent(run),
        case_untouched(run),
        case_mapping(run),
        case_whole(run),
    ]

    ok = True
    print(f"{'case':<40} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<40} {checked:>9}  "
              f"{'ok' if not bad else f'FAIL ({len(bad)})'}")
        for line in bad[:4]:
            print(f"    {line}")
        run.note(f"{label}: {checked} checked, {len(bad)} disagreed"
                 + ("; first: " + bad[0] if bad else ""))

    print()
    for line in run.notes:
        print(f"  · {line}")

    print("\nPASS" if ok else "\nFAIL")
    if broken and ok:
        print("the --broken run tripped nothing: the substitution is not "
              "being reached and these cases are not demonstrating what they "
              "claim.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
