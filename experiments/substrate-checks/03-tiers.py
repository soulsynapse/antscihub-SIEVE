"""Does a store know what it is holding, and admit what it is not?

P2 of `docs/substrate/port-plan.md`. Every case here runs against the fake
route, and none of them needs footage: what a tier does is decided by rows,
forms and budgets, and none of that is about pixels. The one thing that does
touch a codec is the chunk round trip, which encodes synthetic frames and reads
them back.

Two properties, and they are the same property at two scales.

**A store answers for the picture it was asked about, or not at all.** Keyed by
`(form key, row)`, so two pictures of one instant coexist and neither can be
mistaken for the other. The failure this rules out is not an error — it is a
plausible array of the right shape holding the wrong picture, which is why every
fake frame carries its own row number and every assertion reads it back.

**Coverage is recorded, never inferred.** A file present in the directory but
absent from the record is absent, full stop. Both explorers answer this question
by globbing and parsing filenames, which trusts a file being written as much as
a file that is finished; `--broken` restores that, and the case that catches it
is a truncated file sitting where a real chunk would be.

Six cases.

**resident** — get, nearest, coverage, and eviction. Two forms coexist under one
budget; the least-recent unprotected frame goes first; a protected row survives
even when it is the oldest thing there; and a protected set larger than the
budget leaves the store over budget rather than dropping what it was told to
keep, which is the honest failure (ADR-0006).

**nearest** — the bisect against a linear scan over the same data, because the
scan is what it replaces and agreeing with it is the only thing that makes the
replacement safe. Also that a row outside the radius is refused rather than
returned far away.

**roundtrip** — frames into a chunk, chunk published by rename, frames back out.
Row markers must survive, which is what says the store returned the frame it was
asked for rather than a neighbour.

**range** — a frame out of a chunk must be the frame that went in. The case
that found a real defect: grey stored as `yuv420p` is squeezed to limited range
on the way in and read back raw, so black returns as 16 and white as 234, and a
frame from a chunk differs from the same frame in memory by a contrast stretch
nothing reports. Both explorers do this. Extremes are checked rather than an
average, because an average absorbs a squeeze.

**record** — the record survives a reopen; an orphan file is absent; a recorded
file that has been deleted underneath forgets itself instead of answering absent
forever; and a second form over the same rows lands in its own file.

**grid** — chunks sit on an absolute grid, so two windows overlapping the same
ground share chunks rather than each writing the overlap.

**partial** — a truncated file placed where a real chunk would be. Absent,
because it is not in the record, and not because anything inspected it.

**cost** — what recording a span costs as the record grows, timed rather than
asserted (ADR-0008). `Coverage.record` rewrites the whole document, so the
curve decides which threads may call it; `sieve.store.coverage` points here
rather than quoting a number.

`--broken` replaces the record lookup with the directory glob the explorers use.
What it fails is `roundtrip` and `record`: rows that were never written come
back holding another chunk's frames, and a file deleted underneath stays in the
record forever. `partial` keeps passing under it, which is worth saying rather
than tidying away — a *truncated* file is caught by failing to open, which is
luck rather than design, and a complete file holding the wrong frames would sail
straight through. That is the whole argument for a record: the directory can
only tell you a file exists, never that it is the one you wanted.

Run:
    uv run --group experiments python experiments/substrate-checks/03-tiers.py
    uv run --group experiments python experiments/substrate-checks/03-tiers.py --broken
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run, report, time_case  # noqa: E402

from sieve.decode import fake as fake_mod  # noqa: E402
from sieve.decode.fake import FakeRoute  # noqa: E402
from sieve.frame.form import Form  # noqa: E402
from sieve.store.chunks import ChunkStore  # noqa: E402
from sieve.store.coverage import Coverage, Span, digest  # noqa: E402
from sieve.store.resident import ResidentStore  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

ROWS = 480
CROP = Form((0, 0, 64, 48), (64, 48), "gray")
SMALL = Form((0, 0, 64, 48), (32, 24), "gray")   # a second picture of the same
FRAME_BYTES = 64 * 48


def glob_find(self: Coverage, form_key: str, pts: int):
    """`find` as the explorers answer it: whatever is in the directory.

    Kept here as the thing being argued against. It trusts a file being written
    exactly as much as a finished one, which is why both explorers had to bolt
    a "trust it once a newer one exists" rule on top and delete a truncated
    victim by hand after a kill.
    """
    for span in self.spans(form_key):
        if span.holds(pts):
            return span
    for path in sorted(self.directory.glob("*.mp4")):
        return Span(form_key=form_key, start_pts=pts, end_pts=pts, rows=1,
                    filename=path.name)
    return None


def case_resident(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    route = FakeRoute(fake_mod.table(ROWS))
    store = ResidentStore(budget_bytes=10 * FRAME_BYTES)

    for row in range(8):
        store.put(CROP.key(), row, route.image(row))
    # a second picture of instants already held
    for row in range(4):
        store.put(SMALL.key(), row, route.image(row)[:24, :32])

    got = store.get(CROP.key(), 3)
    if got is None or FakeRoute.row_in(got) != 3:
        bad.append("the crop form did not return row 3")
    if store.get(SMALL.key(), 3) is None:
        bad.append("the second form was not held alongside the first")
    if store.get("a form nobody stored", 3) is not None:
        bad.append("a form that was never stored answered")
    if store.forms() != {CROP.key(), SMALL.key()}:
        bad.append(f"forms() said {store.forms()}")

    covered = store.covered(CROP.key(), 2, 6)
    if covered != [2, 3, 4, 5]:
        bad.append(f"covered(2, 6) said {covered}")

    # eviction: least-recent unprotected first, protected survives
    store = ResidentStore(budget_bytes=4 * FRAME_BYTES)
    for row in range(4):
        store.put(CROP.key(), row, route.image(row))
    store.get(CROP.key(), 0)                       # row 0 is now most recent
    store.put(CROP.key(), 4, route.image(4))       # one must go: row 1
    if store.get(CROP.key(), 1) is not None:
        bad.append("eviction did not take the least-recent frame")
    if store.get(CROP.key(), 0) is None:
        bad.append("eviction took a frame that had just been read")

    protected = {(2, CROP.key())}
    for row in range(5, 12):
        store.put(CROP.key(), row, route.image(row), protected=protected)
    if store.get(CROP.key(), 2) is None:
        bad.append("a protected row was evicted")

    over = {(row, CROP.key()) for row in range(20, 30)}
    small = ResidentStore(budget_bytes=2 * FRAME_BYTES)
    for row in range(20, 30):
        small.put(CROP.key(), row, route.image(row), protected=over)
    if len(small) != 10:
        bad.append(f"a protected set larger than the budget lost frames "
                   f"({len(small)} of 10 held)")
    run.note(f"resident: over-budget protected set held {len(small)} frames at "
             f"{small.used_bytes} bytes against a budget of "
             f"{small.budget_bytes} — over budget on purpose, per ADR-0006")
    return "resident (keys, eviction, protection)", 12, bad


def case_nearest(run: Run) -> tuple[str, int, list[str]]:
    """The bisect against the scan it replaces, over the same data."""
    bad: list[str] = []
    route = FakeRoute(fake_mod.table(ROWS))
    store = ResidentStore(budget_bytes=ROWS * FRAME_BYTES)
    held = list(range(0, 400, 7))
    for row in held:
        store.put(CROP.key(), row, route.image(row))

    checked = 0
    for row in range(0, 420):
        answer = store.nearest(CROP.key(), row, radius=12)
        scan = min(held, key=lambda candidate: abs(candidate - row))
        expected = scan if abs(scan - row) <= 12 else None
        if expected is None:
            if answer is not None:
                bad.append(f"nearest({row}) returned {answer[0]} beyond the "
                           "radius")
        elif answer is None:
            bad.append(f"nearest({row}) found nothing; the scan found {scan}")
        elif abs(answer[0] - row) != abs(expected - row):
            bad.append(f"nearest({row}) returned {answer[0]}, scan says "
                       f"{expected}")
        elif answer is not None and FakeRoute.row_in(answer[1]) != answer[0]:
            bad.append(f"nearest({row}) returned row {answer[0]} holding frame "
                       f"{FakeRoute.row_in(answer[1])}")
        checked += 1
    run.note(f"nearest: {checked} rows, bisect agrees with a linear scan over "
             f"{len(held)} held rows")
    return "nearest (bisect equals scan)", checked, bad


def case_roundtrip(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    table = fake_mod.table(ROWS)
    route = FakeRoute(table)
    store = ChunkStore(root / "chunks", table, rows_per_chunk=96)

    frames = [route.image(row) for row in range(96, 192)]
    span = store.encode(CROP, 96, frames)
    if span is None:
        bad.append("encoding a complete run returned no span")
        return "roundtrip (encode, publish, read)", 0, bad

    if span.start_pts != table.pts_of(96) or span.end_pts != table.pts_of(191):
        bad.append("the recorded span does not name the timestamps written")
    if (root / "chunks" / span.filename).stat().st_size == 0:
        bad.append("the published file is empty")

    checked = 0
    for row in (96, 97, 143, 190, 191):
        got = store.fetch(CROP.key(), row)
        if got is None:
            bad.append(f"row {row} was written and read back absent")
            continue
        if FakeRoute.row_in(got) != row:
            bad.append(f"row {row} read back as frame {FakeRoute.row_in(got)}")
        checked += 1

    for row in (95, 192, 300):
        if store.fetch(CROP.key(), row) is not None:
            bad.append(f"row {row} was never written and answered")
    if store.fetch(SMALL.key(), 100) is not None:
        bad.append("a form that was never written answered")
    run.note(f"roundtrip: {checked} rows written and read back with their row "
             "markers intact through a lossy intra encode")
    store.close()
    return "roundtrip (encode, publish, read)", checked, bad


def case_range(run: Run, root: Path) -> tuple[str, int, list[str]]:
    """A frame from memory and the same frame from a chunk must be one frame.

    The case that found the defect. Storing grey as `yuv420p` applies the
    limited-range convention on the way in — 0 becomes 16, 255 becomes 234 —
    while the read side takes the luma plane raw and does not undo it, so the
    round trip is a contrast squeeze. Both explorers do exactly this, which
    means a frame served from a chunk and the same frame served from RAM differ
    by a stretch that nothing reports: the shape is right, the picture looks
    right, and every value computed downstream depends on which tier answered.

    Extremes rather than an average, because a squeeze is a change of range and
    an average would absorb it. A mid-grey survives either way, which is why
    this went unnoticed everywhere it has been written.
    """
    bad: list[str] = []
    table = fake_mod.table(ROWS)
    directory = root / "range"
    store = ChunkStore(directory, table, rows_per_chunk=96)

    # a deliberate test card: full black, full white, and two mid tones
    card = np.zeros((48, 64), dtype=np.uint8)
    for index, value in enumerate((0, 96, 255, 128)):
        card[:8, index * 8:(index + 1) * 8] = value
    frames = [card.copy() for _ in range(96)]
    if store.encode(CROP, 0, frames) is None:
        bad.append("the test card did not encode")
        return "range (chunk equals memory)", 0, bad

    got = store.fetch(CROP.key(), 10)
    if got is None:
        bad.append("the test card read back absent")
        return "range (chunk equals memory)", 0, bad

    wanted = [0, 96, 255, 128]
    read = [int(np.median(got[:8, i * 8:(i + 1) * 8])) for i in range(4)]
    # lossy at this quality moves a flat block by a count or two; a range
    # squeeze moves black to 16 and white to 234, which is not that
    for value, back in zip(wanted, read):
        if abs(back - value) > 4:
            bad.append(f"stored {value}, read back {back} — a shift this size "
                       "is a range conversion, not quantisation")
    run.note(f"range: wrote {wanted}, read {read} through a chunk; black and "
             "white must stay black and white or the tiers disagree")
    store.close()
    return "range (chunk equals memory)", len(wanted), bad


def case_record(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    table = fake_mod.table(ROWS)
    route = FakeRoute(table)
    directory = root / "record"
    store = ChunkStore(directory, table, rows_per_chunk=96)
    store.encode(CROP, 0, [route.image(row) for row in range(96)])
    small = store.encode(SMALL, 0,
                         [route.image(row)[:24, :32] for row in range(96)])
    if small is None:
        bad.append("a second form over the same rows did not encode")
    elif len({s.filename for s in store.coverage.spans()}) != 2:
        bad.append("two forms over the same rows shared one file")
    store.close()

    reopened = ChunkStore(directory, table, rows_per_chunk=96)
    if reopened.fetch(CROP.key(), 40) is None:
        bad.append("a reopened store could not read what it had written")
    if len(reopened.coverage) != 2:
        bad.append(f"the record came back with {len(reopened.coverage)} spans")

    # a recorded file deleted underneath: absent, and forgotten so the next
    # request does not go looking again
    span = reopened.coverage.spans(CROP.key())[0]
    reopened.release(span.filename)
    (directory / span.filename).unlink()
    if reopened.fetch(CROP.key(), 40) is not None:
        bad.append("a deleted file still answered")
    if reopened.coverage.find(CROP.key(), table.pts_of(40)) is not None:
        bad.append("a deleted file stayed in the record")
    reopened.close()
    run.note("record: survives a reopen, two forms over one row range keep "
             "separate files, a vanished file forgets itself")
    return "record (reopen, two forms, vanished)", 3, bad


def case_grid(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    table = fake_mod.table(ROWS)
    store = ChunkStore(root / "grid", table, rows_per_chunk=96)
    for row, expected in ((0, 0), (95, 0), (96, 96), (100, 96), (383, 288)):
        if store.chunk_start(row) != expected:
            bad.append(f"chunk_start({row}) said {store.chunk_start(row)}, "
                       f"not {expected}")
    store.close()
    return "grid (absolute, not window-relative)", 5, bad


def case_partial(run: Run, root: Path) -> tuple[str, int, list[str]]:
    """A truncated file where a real chunk would be. Absent, or the record lies."""
    bad: list[str] = []
    table = fake_mod.table(ROWS)
    route = FakeRoute(table)
    directory = root / "partial"
    store = ChunkStore(directory, table, rows_per_chunk=96)

    # what a killed encoder leaves behind: the right name, the wrong contents,
    # and nothing in the record
    filename = f"{digest(CROP.key(), table.pts_of(0))}.mp4"
    (directory / filename).write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64)

    if store.fetch(CROP.key(), 10) is not None:
        bad.append("a truncated file with no record entry answered")
    if store.holds(CROP.key(), 10):
        bad.append("a truncated file with no record entry read as held")

    # and the same ground, once genuinely written, does answer
    store.encode(CROP, 0, [route.image(row) for row in range(96)])
    got = store.fetch(CROP.key(), 10)
    if got is None:
        bad.append("the real chunk did not answer after replacing the orphan")
    elif FakeRoute.row_in(got) != 10:
        bad.append(f"the real chunk answered with frame "
                   f"{FakeRoute.row_in(got)}")
    store.close()
    run.note("partial: a truncated file is absent because it is not in the "
             "record, not because anything inspected it")
    return "partial (orphan file is absent)", 2, bad


def case_record_cost(run: Run, root: Path) -> None:
    """What a span costs to record, as the record grows.

    Not an assertion and not a threshold (ADR-0008). `Coverage.record`
    serialises every span it holds and renames the document into place, so
    adding one gets dearer as there are more, and the shape of that curve
    decides where this may be called from. Recorded here so the docstring in
    `sieve.store.coverage` can point at a number instead of carrying one, and
    so a later measurement supersedes this by sitting beside it.
    """
    coverage = Coverage(root / "cost")
    spans = 0

    def record_batch():
        nonlocal spans
        for _ in range(120):
            coverage.record(Span("f", spans * 96, spans * 96 + 95, 96,
                                 f"{spans}.mp4"))
            spans += 1
            yield spans

    report(time_case(run, "coverage.record (first 120)", record_batch,
                     params={"spans_before": 0}, warmup=1,
                     unit="ms per record"))
    report(time_case(run, "coverage.record (spans 120-240)", record_batch,
                     params={"spans_before": 120}, warmup=1,
                     unit="ms per record"))
    report(time_case(run, "coverage.record (spans 240-360)", record_batch,
                     params={"spans_before": 240}, warmup=1,
                     unit="ms per record"))


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        Coverage.find = glob_find

    run = Run(
        experiment="P2-tiers" + ("-broken" if broken else ""),
        question="Does a store answer only for the picture it was asked "
                 "about, and only for what the record says it holds?",
    )
    run.note("no footage: every case runs against the fake route, because what "
             "a tier does is decided by rows, forms and budgets")
    if broken:
        run.note("RUN WITH --broken: the record lookup is replaced by the "
                 "directory glob both explorers use. `partial` is expected to "
                 "FAIL — a file being written is trusted as much as one that "
                 "is finished.")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        results = [
            case_resident(run),
            case_nearest(run),
            case_roundtrip(run, root),
            case_range(run, root),
            case_record(run, root),
            case_grid(run, root),
            case_partial(run, root),
        ]
        print()
        print("cost (recorded, not a threshold):")
        case_record_cost(run, root)
        print()

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
        print("the --broken run tripped nothing: the glob is not being "
              "reached, and `partial` is not demonstrating what it claims.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
