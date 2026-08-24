"""Does a row still name the frame it named, after every trip it takes?

P0 of `docs/archive/2026.08-substrate-port.md`. One property, in one sentence: **a row and
a presentation timestamp convert to each other without loss, and nothing else
may claim to do that conversion.**

The second clause is the one with teeth. Both explorers compute a frame's pts as
`start + row / rate / timebase` rather than looking it up, and it works, because
every consumer of it carries a half-frame tolerance. So this file has to show
that the arithmetic is actually wrong, or it is an argument about tidiness.

It is wrong two ways, and only one of them is the way ADR-0004 leads with.
*Rounding*: at a 90 kHz timebase over 24000/1001 fps a frame is 3753.75 ticks,
the true sequence has alternating spacing, and multiply-and-truncate disagrees
with it — but only ever by a tick, which is exactly what a half-frame tolerance
is for. That failure is bounded and, on its own, survivable. *The head*: this
tree's own footage was cut mid-GOP, so its first packets carry timestamps below
the stream'"'"'s stated start, and anything that begins counting at `start_time`
is offset by the length of that head for the whole file. On this source that is
twenty frames, on every row, silently, and no frame-scale tolerance touches it.
The second is the one that would have bitten, and it is not the rounding case —
worth knowing before dismissing the arithmetic as merely imprecise.

Six cases, in increasing dependence on the world.

**synthetic** — two tables built by hand, no file involved: one on the awkward
90 kHz pairing, one shaped like this tree'"'"'s footage. Round-trip every row of
each, and measure how far the arithmetic route falls from each. This is the
case that stays runnable on a machine with no `video-tests/`.

**table** — the real 5.3K source, demuxed. Timestamps strictly ascending, every
row round-tripping, and every keyframe answer landing on a keyframe at or before
what was asked. The GOP figure is reported so it can be set beside
`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`
rather than restated here.

**counts** — the three answers to "how many frames". Metadata and packets are
both available without decoding and are compared; the decodable count is not
knowable here at any price and is left to P1, where a route asks for pixels and
gets none.

**cache** — a saved table reads back identical, and one whose source has been
touched since reads back as absent rather than stale. The second is the whole
reason the sidecar carries a fingerprint.

**derived** — what ADR-0004 rests a lot of weight on. The claim is *not* that
row *r* of a proxy is row *r* of its source; this case disproves that, and finds
the constant twenty independently. The claim is that every instant the proxy
holds is an instant the source holds, named identically once rescaled, with
nothing stored to say so — which holds exactly, and is what makes the twenty
harmless rather than hidden.

**forms** — the property `form.py` exists to have: building a form from a source
frame and deriving it through an `EXACT` intermediate produce the same bytes, so
a warm answer cannot differ from a cold one and cache state cannot reach a
measurement.

`--broken` replaces the table lookup with the arithmetic route wherever a check
uses one. `synthetic` and `table` must fail; `derived` is insensitive to it by
construction, because it maps pts to pts and never asks a row for its timestamp,
which is the arrangement that makes the head harmless in the first place.

Run:
    uv run --group experiments python experiments/substrate-checks/01-identity.py
    uv run --group experiments python experiments/substrate-checks/01-identity.py --broken
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE, Run  # noqa: E402

from sieve.frame import Form, FrameTable, Shape, build, derive, grade, rescale  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
PROXY = FOOTAGE / "derived" / "proxy-1328-intra.mp4"

#: The awkward pairing ADR-0004 names: a frame lasts 3753.75 ticks, so no
#: integer number of ticks is a frame and the arithmetic route rounds every one.
TICKS = Fraction(1, 90_000)
RATE = Fraction(24_000, 1001)
SYNTHETIC_ROWS = 12_000
SYNTHETIC_GOP = 24


def arithmetic_pts(table: FrameTable, row: int, rate: Fraction) -> int:
    """What both explorers compute instead of looking it up.

    Kept here rather than imported because nothing in `src/sieve/` should
    contain it — this file is the only place it survives, as the thing being
    argued against.
    """
    step = Fraction(1, 1) / (rate * table.timebase)
    return table.start_pts + int(step * row)


def _table(stamps: np.ndarray, timebase: Fraction) -> FrameTable:
    keyframes = np.zeros(len(stamps), dtype=bool)
    keyframes[::SYNTHETIC_GOP] = True
    return FrameTable(pts=np.ascontiguousarray(stamps), keyframe=keyframes,
                      timebase=timebase, start_pts=0)


def skewed_table() -> FrameTable:
    """A 90 kHz stream at 23.976 — the pairing ADR-0004 names.

    True timestamps, not computed ones: a frame lasts 3753.75 ticks, so a real
    encoder writes a sequence whose spacing alternates and whose *n*th entry is
    the exact rational rounded. That is what the arithmetic route, which
    multiplies and truncates, cannot reproduce.
    """
    step = Fraction(90_000) * Fraction(1001, 24_000)   # 3753.75 ticks
    stamps = np.array([round(Fraction(i) * step) for i in range(SYNTHETIC_ROWS)],
                      dtype=np.int64)
    return _table(stamps, TICKS)


def cut_table() -> FrameTable:
    """The shape of the footage in this tree: an integer step, a negative head.

    Whole ticks per frame, so no rounding is involved and the arithmetic route
    looks safe — and it is wrong anyway, because the file was cut mid-GOP and
    its leading packets carry timestamps before the stream's stated start.
    Anything that begins counting at `start_time` is offset by the length of
    that head for the whole rest of the file.
    """
    step, head = 1001, 20
    stamps = np.array([(i - head) * step for i in range(SYNTHETIC_ROWS)],
                      dtype=np.int64)
    return _table(stamps, Fraction(1, 24_000))


def roundtrip(table: FrameTable, broken: bool, rate: Fraction) -> list[str]:
    """Every row to a timestamp and back. The core property."""
    bad: list[str] = []
    for row in range(len(table)):
        stamp = (arithmetic_pts(table, row, rate) if broken
                 else table.pts_of(row))
        back = table.row_of(stamp)
        if back != row:
            bad.append(f"row {row} -> pts {stamp} -> "
                       f"{'no row' if back is None else f'row {back}'}")
            if len(bad) >= 8:
                bad.append("... further disagreements not listed")
                return bad
    return bad


def case_synthetic(run: Run, broken: bool) -> tuple[str, int, list[str]]:
    """Two hand-built tables, two independent ways the arithmetic is wrong."""
    bad: list[str] = []
    checked = 0
    for label, table, rate, ticks in (
        ("skewed timebase", skewed_table(), RATE, TICKS),
        ("cut head", cut_table(), RATE, Fraction(1, 24_000)),
    ):
        checked += len(table)
        bad += [f"{label}: {line}" for line in roundtrip(table, broken, rate)]

        # the second clause: the arithmetic route must be shown to be wrong on
        # each table, or that sub-case is an argument about tidiness
        gaps = np.array([arithmetic_pts(table, row, rate) - table.pts_of(row)
                         for row in range(len(table))], dtype=np.int64)
        wrong = np.flatnonzero(gaps)
        if not len(wrong):
            bad.append(f"{label}: the arithmetic route never diverged, so this "
                       "sub-case is not testing what it says")
            continue
        worst = int(np.abs(gaps).max())
        run.note(
            f"synthetic/{label}: arithmetic disagrees on {len(wrong)} of "
            f"{len(table)} rows, first at row {int(wrong[0])}, worst by "
            f"{worst} ticks ({worst * float(ticks) * 1000:.1f} ms, "
            f"{worst * float(ticks) * float(rate):.2f} frames)"
            + ("; bounded, so a half-frame tolerance hides it"
               if worst * float(ticks) * float(rate) < 0.5 else
               "; unbounded by any frame-scale tolerance"))
    return "synthetic (no footage)", checked, bad


def case_table(run: Run, broken: bool) -> tuple[str, int, list[str]]:
    if not BIG.exists():
        run.note(f"table: skipped, {BIG.name} absent")
        return "table (5.3K source)", 0, []
    shape = Shape.read(BIG)
    table = FrameTable.build(BIG)
    bad: list[str] = []

    if not np.all(np.diff(table.pts) > 0):
        bad.append("timestamps are not strictly ascending after sorting")
    if table.duplicate_pts:
        run.note(f"table: {table.duplicate_pts} packets repeated a pts already "
                 "seen and were dropped")

    bad += roundtrip(table, broken, shape.average_rate)

    for row in range(0, len(table), max(1, len(table) // 400)):
        landed = table.keyframe_at_or_before(row)
        if landed > row:
            bad.append(f"keyframe for row {row} landed ahead at {landed}")
        elif not bool(table.keyframe[landed]):
            bad.append(f"keyframe for row {row} landed on {landed}, not a "
                       "keyframe")

    gaps = np.diff(np.flatnonzero(table.keyframe))
    if len(gaps):
        run.note(f"table: {int(table.keyframe.sum())} keyframes, gap "
                 f"min={int(gaps.min())} median={int(np.median(gaps))} "
                 f"max={int(gaps.max())}")
    run.note(f"table: {shape.codec} {shape.width}x{shape.height}, "
             f"period {shape.frame_period_ms:.3f} ms, probe key "
             f"{shape.probe_key()}")
    return "table (5.3K source)", len(table), bad


def case_counts(run: Run) -> tuple[str, int, list[str]]:
    if not BIG.exists():
        run.note("counts: skipped, source absent")
        return "counts (metadata vs packets)", 0, []
    probed = harness.probe(BIG)
    table = FrameTable.build(BIG)
    metadata = probed.get("nb_frames")
    run.note(f"counts: metadata says {metadata}, packets say {len(table)}, "
             "decodable images are P1's to report — a demux-only pass cannot "
             "know them")
    bad: list[str] = []
    if metadata is not None and int(metadata) == len(table):
        run.note("counts: metadata and packets agree on this file, so the "
                 "three-way disagreement is not exercised here")
    return "counts (metadata vs packets)", len(table), bad


def case_cache(run: Run) -> tuple[str, int, list[str]]:
    if not BIG.exists():
        run.note("cache: skipped, source absent")
        return "cache (save, load, staleness)", 0, []
    bad: list[str] = []
    table = FrameTable.build(BIG)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        copy = root / BIG.name
        shutil.copy2(BIG, copy)          # copy2 keeps mtime, so does the sidecar
        path = root / "table.npz"
        table.save(path, copy)

        back = FrameTable.load(path, copy)
        if back is None:
            bad.append("a table saved and reloaded from an untouched source "
                       "read as absent")
        else:
            if not np.array_equal(back.pts, table.pts):
                bad.append("reloaded timestamps differ")
            if not np.array_equal(back.keyframe, table.keyframe):
                bad.append("reloaded keyframe flags differ")
            if back.timebase != table.timebase:
                bad.append(f"reloaded timebase {back.timebase} != "
                           f"{table.timebase}")

        copy.write_bytes(copy.read_bytes() + b"\0")   # the source moved
        if FrameTable.load(path, copy) is not None:
            bad.append("a table whose source changed underneath still loaded")
    return "cache (save, load, staleness)", len(table), bad


def case_derived(run: Run) -> tuple[str, int, list[str]]:
    if not (BIG.exists() and PROXY.exists()):
        run.note("derived: skipped, source or proxy absent")
        return "derived (proxy maps frame-for-frame)", 0, []
    src, dst = FrameTable.build(BIG), FrameTable.build(PROXY)
    bad: list[str] = []
    run.note(f"derived: source timebase {src.timebase_str} over {len(src)} "
             f"rows, proxy {dst.timebase_str} over {len(dst)} rows")

    # the actual claim: every instant the proxy holds is an instant the source
    # holds, named identically once rescaled. Not "row r is row r" — that is
    # the thing being disproved below.
    checked = 0
    offsets: set[int] = set()
    for row in range(len(dst)):
        wanted = rescale(dst.pts_of(row) - dst.start_pts,
                         dst.timebase, src.timebase) + src.start_pts
        landed = src.row_of(wanted)
        if landed is None:
            bad.append(f"proxy row {row} (pts {dst.pts_of(row)}) names an "
                       "instant the source does not contain")
            if len(bad) >= 8:
                break
            continue
        offsets.add(landed - row)
        checked += 1

    if len(offsets) == 1 and not bad:
        (offset,) = offsets
        run.note(f"derived: every one of {checked} proxy rows names a source "
                 f"instant exactly, through rescale alone with nothing stored. "
                 f"By *row* the two disagree by a constant {offset} — ADR-0004's "
                 f"twenty, arrived at independently: the source's first "
                 f"{offset} packets carry timestamps below its stated start "
                 f"and ffmpeg dropped them. A tool indexing by position would "
                 f"be {offset} frames wrong for the whole file and never say so.")
    elif offsets and not bad:
        run.note(f"derived: proxy-to-source row offset is not constant "
                 f"({min(offsets)}..{max(offsets)}), which pts mapping "
                 "absorbs and row mapping could not")

    head = int((src.pts < src.start_pts).sum())
    run.note(f"derived: {head} source packets carry a pts below the stream's "
             f"stated start of {src.start_pts}; that this equals the packet "
             "shortfall is consistent with them being the undecodable head, "
             "and P1 confirms it by asking for pixels and getting none")

    # this case is insensitive to --broken by construction, and says so: it
    # maps pts to pts and never asks a row for its timestamp, which is the
    # arrangement that makes the head harmless rather than the one that hides
    # it. What --broken breaks is `table`, three cases up, where row 0 comes
    # back as row 20.
    return "derived (proxy maps by pts, not by row)", checked, bad


def case_forms(run: Run) -> tuple[str, int, list[str]]:
    """Cold and warm must agree, or a cache can reach a measurement."""
    rng = np.random.default_rng(7)
    frame = rng.integers(0, 256, size=(720, 1280, 3), dtype=np.uint8)
    held = Form((100, 60, 800, 600), (800, 600), "bgr")      # native, containing
    wanted = Form((240, 180, 320, 240), (160, 120), "gray")  # a resampled crop
    bad: list[str] = []

    if grade(held, wanted) is None:
        bad.append("a native containing form was refused for a sub-crop")
        return "forms (cold equals warm)", 0, bad

    cold = build(frame, wanted)
    warm, how = derive(build(frame, held), held, wanted)
    if how != "exact":
        bad.append(f"deriving through a native containing form graded {how}")
    if cold.shape != warm.shape:
        bad.append(f"shapes differ: {cold.shape} vs {warm.shape}")
    elif not np.array_equal(cold, warm):
        differing = int((cold != warm).sum())
        bad.append(f"cold and warm differ in {differing} of {cold.size} bytes")

    approx = Form((240, 180, 320, 240), (320, 240), "gray")
    downsampled = Form((100, 60, 800, 600), (400, 300), "bgr")
    if grade(downsampled, approx) != "approx":
        bad.append("an already-resampled form did not grade approx")
    return "forms (cold equals warm)", cold.size, bad


def main() -> None:
    broken = "--broken" in sys.argv
    run = Run(
        experiment="P0-identity" + ("-broken" if broken else ""),
        question="Does a row and a pts convert to each other without loss, "
                 "and is the arithmetic route it replaces actually wrong?",
    )
    for path in (BIG, PROXY):
        if path.exists():
            run.add_footage(path)
    if broken:
        run.note("RUN WITH --broken: the table lookup is replaced by "
                 "`start + round(row / rate / timebase)` wherever a check uses "
                 "it. Cases that can see the difference are expected to FAIL.")

    results = [
        case_synthetic(run, broken),
        case_table(run, broken),
        case_counts(run),
        case_cache(run),
        case_derived(run),
        case_forms(run),
    ]

    ok = True
    print(f"{'case':<38} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<38} {checked:>9}  "
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
        print("the --broken run did not trip any check: the arithmetic route "
              "and the table agree on this footage, so these cases are not "
              "demonstrating the property they claim.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
