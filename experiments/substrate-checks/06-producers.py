"""Do the background producers work in the order they claim to?

P5 of `docs/substrate/port-plan.md`. Both producers are split into a pure
schedule and an impure worker, and the whole reason is this file: **an order is
a list, and a list can be compared.** In the explorers the fill order is four
lines inside a thread body and the batch order is a method on a class holding a
subprocess handle, so the only way to observe either is to decode video and
watch a picture — which is how the fill order was got wrong in the first place,
and the finding says so plainly: the same decode work in a different order is
the difference between a frozen landing and a seamless one.

Nothing here launches ffmpeg. The builder takes its launcher as an argument and
the check hands it one that touches files, so the schedule, the redirect, the
publication rule and the resume are all exercised with no encoder, no footage
and no waiting.

Eight cases.

**order** — the fill order is the playhead's chunk first, then forward, then
wrapping to the window's start. Checked at the window's beginning, middle and
end, and for an anchor outside the window entirely.

**pieces** — pieces sit on the absolute grid and are clipped to the window, so
two windows overlapping the same ground share chunks. Only a piece that covers
its chunk exactly is whole; a version of this that checked alignment alone
called a sixteen-row tail whole, which would have written a chunk with a hole
in it.

**disk** — a piece whose rows are already persisted is marked as a read before
anything runs, so a landing can be priced without starting one.

**fill** — the frontier against the fake route: rows arrive in the order the
schedule gave, whole chunks are written and partial ones are not, and a second
fill over the same window reads from disk instead of decoding again.

**pause** — a paused frontier stops asking the route for rows and resumes where
it left off. This is the priority inversion the plan calls for, and a fill that
could not yield would make it impossible.

**batches** — the proxy schedule: nearest unfinished batch to attention, ties
to the lower index so two runs from one state agree, and a resume that builds
only what is missing.

**redirect** — a batch in flight is abandoned when attention moves far *and*
there is nearer work, and not otherwise. The second condition is what stops it
thrashing between two equally distant batches.

**geometry** — the form the builder records describes the pixels ffmpeg
actually writes. Added after driving the builder against real ffmpeg found the
record saying `1328x746` for segments that were `1328x748`: `scale=W:-2` rounds
the free dimension to the nearest even number, and truncating instead is off by
two often enough to matter.

`--broken` fills from the window's start instead of the playhead's chunk, which
is exactly what the explorer did before the finding, and `order` and `fill` both
fail.

Run:
    uv run --group experiments python experiments/substrate-checks/06-producers.py
    uv run --group experiments python experiments/substrate-checks/06-producers.py --broken
"""

from __future__ import annotations

import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.decode import fake as fake_mod  # noqa: E402
from sieve.decode.fake import FakeRoute  # noqa: E402
from sieve.frame.form import Form  # noqa: E402
from sieve.session import frontier as frontier_mod  # noqa: E402
from sieve.session.frontier import Frontier, fill_order  # noqa: E402
from sieve.session.ledger import Ledger  # noqa: E402
from sieve.frame.shape import Shape  # noqa: E402
from sieve.store.build import (  # noqa: E402
    Batch,
    FFmpegLauncher,
    ProxyBuilder,
    missing_batches,
    next_batch,
    should_redirect,
)
from sieve.store.chunks import ChunkStore  # noqa: E402
from sieve.store.resident import ResidentStore  # noqa: E402
from sieve.store.spans import SpanStore  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

ROWS = 960
CHUNK = 96
FORM = Form((0, 0, 64, 48), (64, 48), "gray")
FRAME_BYTES = 64 * 48


def from_the_start(start, end, anchor, rows_per_chunk, held=None):
    """`fill_order` as the explorer did it before the finding.

    Kept here as the thing being argued against. It is the obvious order —
    fill the window from its beginning — and it is why a landing used to sit
    frozen for a couple of seconds: the loop plays from where somebody
    clicked, and the frontier spends its first seconds decoding ground nobody
    is looking at.
    """
    return fill_order(start, end, start, rows_per_chunk, held)


class TouchLauncher:
    """A launcher that writes segment files instantly and decodes nothing.

    Enough to exercise the schedule, the publication rule and the redirect,
    which are the parts with decisions in them. What it cannot say anything
    about is what building a proxy costs — that is `storage-experiments`, and
    a number taken against this would be a number about `Path.touch`.
    """

    def __init__(self, per_call: int = 2):
        self.per_call = per_call
        self.launched: list[Batch] = []
        self.terminated = 0

    def launch(self, batch: Batch, staging: Path):
        staging.mkdir(parents=True, exist_ok=True)
        self.launched.append(batch)
        written = []
        for index in list(batch)[: self.per_call]:
            path = staging / f"seg-{index:05d}.mp4"
            path.write_bytes(b"segment")
            written.append(index)
        return {"batch": batch, "written": written, "done": False}

    def poll(self, handle):
        # one tick in flight, then finished — enough for a check to see both
        if handle["done"]:
            return 0
        handle["done"] = True
        return None

    def terminate(self, handle) -> None:
        self.terminated += 1
        handle["done"] = True


def case_order(run: Run) -> tuple[str, int, list[str]]:
    order = frontier_mod.fill_order
    bad: list[str] = []

    middle = [p.start for p in order(0, 480, 250, CHUNK)]
    if middle[0] != 192:
        bad.append(f"anchored at 250 the fill starts at {middle[0]}, not the "
                   "chunk holding the playhead")
    if middle != [192, 288, 384, 0, 96]:
        bad.append(f"anchored at 250 the order is {middle}")

    at_start = [p.start for p in order(0, 480, 10, CHUNK)]
    if at_start != [0, 96, 192, 288, 384]:
        bad.append(f"anchored at the window start the order is {at_start}")

    at_end = [p.start for p in order(0, 480, 470, CHUNK)]
    if at_end != [384, 0, 96, 192, 288]:
        bad.append(f"anchored at the window end the order is {at_end}")

    outside = [p.start for p in order(100, 400, 9999, CHUNK)]
    if outside[0] != 384:
        bad.append(f"an anchor past the window did not clamp: {outside}")

    covered = {p.start for p in order(0, 480, 250, CHUNK)}
    if len(covered) != 5:
        bad.append(f"the order covers {len(covered)} distinct pieces, not 5")
    run.note(f"order: anchored mid-window the fill runs {middle} — the "
             "playhead's chunk, forward, then wrapping")
    return "order (playhead first, then wrap)", 5, bad


def case_pieces(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    pieces = fill_order(100, 400, 100, CHUNK)
    by_grid = {p.grid_start: p for p in pieces}

    if sorted(by_grid) != [96, 192, 288, 384]:
        bad.append(f"pieces sit on {sorted(by_grid)}, not the absolute grid")
    head = by_grid[96]
    if head.start != 100 or head.whole:
        bad.append(f"the leading piece {head.start}..{head.end} is clipped and "
                   "must not read as whole")
    tail = by_grid[384]
    if tail.rows != 16 or tail.whole:
        bad.append(f"the trailing piece covers {tail.rows} rows and reports "
                   f"whole={tail.whole}; only a full chunk is whole")
    for grid in (192, 288):
        if not by_grid[grid].whole:
            bad.append(f"the interior piece at {grid} is not whole")

    # two windows over the same ground must land on the same grid
    other = {p.grid_start for p in fill_order(150, 350, 200, CHUNK)}
    if not other <= set(by_grid) | {96, 192, 288, 384}:
        bad.append(f"a second window used a different grid: {sorted(other)}")
    run.note(f"pieces: {len(pieces)} on the absolute grid, "
             f"{sum(1 for p in pieces if p.whole)} whole")
    return "pieces (grid, clipped, whole)", len(pieces), bad


def case_disk(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    pieces = fill_order(0, 480, 0, CHUNK, held=[(96, 192), (288, 384)])
    marked = {p.start: p.from_disk for p in pieces}
    if marked != {0: False, 96: True, 192: False, 288: True, 384: False}:
        bad.append(f"held ranges were read as {marked}")
    partial = fill_order(100, 400, 100, CHUNK, held=[(96, 192)])
    lead = next(p for p in partial if p.grid_start == 96)
    if not lead.from_disk:
        bad.append("a clipped piece inside a held range was not marked as a "
                   "read")
    run.note("disk: each piece says read or decode before the fill starts, so "
             "a landing can be priced without starting one")
    return "disk (priced before it runs)", 5, bad


def case_fill(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    table = fake_mod.table(ROWS)
    route = FakeRoute(table)
    resident = ResidentStore(budget_bytes=ROWS * FRAME_BYTES)
    chunks = ChunkStore(root / "fill", table, rows_per_chunk=CHUNK)
    book = Ledger()

    frontier = Frontier(route, FORM, resident, chunks, ledger=book)
    order = frontier.launch(0, 288, 100)
    if not frontier.wait():
        bad.append("the fill did not finish")
    frontier.stop()

    wanted = [row for piece in order for row in range(piece.start, piece.end)]
    if route.asked != wanted:
        head_got, head_want = route.asked[:4], wanted[:4]
        bad.append(f"the route was asked {head_got}... where the schedule said "
                   f"{head_want}...")
    # unconditional: a fill told the playhead is at 100 begins at its chunk,
    # and guarding this on the mode would have let --broken pass the case it
    # exists to break
    if route.asked[0] != 96:
        bad.append(f"the fill began at row {route.asked[0]} rather than at 96, "
                   "the chunk holding the playhead")
    if resident.get(FORM.key(), 100) is None:
        bad.append("a filled row is not resident")
    got = resident.get(FORM.key(), 150)
    if got is not None and FakeRoute.row_in(got) != 150:
        bad.append(f"row 150 holds frame {FakeRoute.row_in(got)}")

    held = chunks.rows_held(FORM.key())
    if held != [(0, 96), (96, 192), (192, 288)]:
        bad.append(f"whole chunks written as {held}")

    # second fill over the same ground: reads, does not decode
    route.reset()
    again = Frontier(route, FORM, resident, chunks)
    order2 = again.launch(0, 288, 100)
    if not again.wait():
        bad.append("the refill did not finish")
    again.stop()
    if any(not piece.from_disk for piece in order2):
        bad.append("a refill over persisted ground still planned to decode")
    if route.asked:
        bad.append(f"a refill asked the route for {len(route.asked)} rows")
    if again.from_disk != 288:
        bad.append(f"the refill read {again.from_disk} rows from disk, not 288")
    run.note(f"fill: {frontier.from_route} rows decoded then "
             f"{again.from_disk} read back from {len(held)} chunks, with the "
             "route untouched on the second pass")
    chunks.close()
    return "fill (schedule drives the thread)", len(wanted), bad


def case_pause(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    table = fake_mod.table(ROWS)
    route = FakeRoute(table, delay_s=0.002)
    resident = ResidentStore(budget_bytes=ROWS * FRAME_BYTES)
    chunks = ChunkStore(root / "pause", table, rows_per_chunk=CHUNK)

    frontier = Frontier(route, FORM, resident, chunks)
    frontier.launch(0, 480, 0)
    time.sleep(0.05)
    frontier.pause.set()
    time.sleep(0.05)
    asked_when_paused = len(route.asked)
    time.sleep(0.1)
    if len(route.asked) != asked_when_paused:
        bad.append(f"a paused frontier asked for "
                   f"{len(route.asked) - asked_when_paused} more rows")
    frontier.pause.clear()
    time.sleep(0.1)
    if len(route.asked) <= asked_when_paused:
        bad.append("the frontier did not resume after the pause was cleared")
    if frontier.paused_s <= 0:
        bad.append("the pause was not accounted for")
    frontier.stop(wait=True)
    run.note(f"pause: held at {asked_when_paused} rows for "
             f"{frontier.paused_s * 1000:.0f} ms, then resumed")
    chunks.close()
    return "pause (yields the decoder)", asked_when_paused, bad


def case_batches(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    segments = 40
    empty: set[int] = set()

    if len(missing_batches(empty, segments, 4)) != 10:
        bad.append(f"{len(missing_batches(empty, segments, 4))} batches over "
                   f"{segments} segments at 4 apiece")
    if next_batch(empty, segments, 0, 4) != Batch(0, 4):
        bad.append("attention at zero did not choose the first batch")
    near = next_batch(empty, segments, 21, 4)
    if near != Batch(20, 4):
        bad.append(f"attention at 21 chose {near}")

    # ties to the lower index, so two runs from one state agree
    tie = next_batch(empty, segments, 10, 4)
    if tie != Batch(8, 4):
        bad.append(f"a tie at 10 chose {tie} rather than the lower index")

    # resume: only what is missing, and still nearest first
    present = set(range(0, 20))
    resumed = missing_batches(present, segments, 4)
    if [b.start for b in resumed] != [20, 24, 28, 32, 36]:
        bad.append(f"a resume planned {[b.start for b in resumed]}")
    if next_batch(present, segments, 35, 4) != Batch(32, 4):
        bad.append("a resume did not order by distance from attention")
    if next_batch(set(range(segments)), segments, 0, 4) is not None:
        bad.append("a finished build still had work")
    run.note("batches: nearest unfinished to attention, ties to the lower "
             "index, and a resume plans only what is missing")
    return "batches (nearest, stable, resumable)", 10, bad


def case_redirect(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    segments, present = 40, set()

    running = Batch(0, 4)
    if should_redirect(running, 3, present, segments, 4, 8):
        bad.append("attention inside the threshold caused a redirect")
    if not should_redirect(running, 30, present, segments, 4, 8):
        bad.append("attention far away with nearer work did not redirect")
    # far, but nothing nearer to go to: abandoning a batch in flight for an
    # equally distant one is how this thrashes
    nearly_done = set(range(4, segments))
    if should_redirect(running, 30, nearly_done, segments, 4, 8):
        bad.append("redirected with no unfinished work nearer than the batch "
                   "in flight")

    # and the builder end to end, against a launcher that touches files
    table = fake_mod.table(ROWS)
    store = SpanStore(root / "proxy", table)
    (root / "proxy").mkdir(parents=True, exist_ok=True)
    launcher = TouchLauncher(per_call=4)
    builder = ProxyBuilder(store, table, FORM.key(), launcher,
                           segments=ROWS // CHUNK, rows_per_segment=CHUNK)
    for _ in range(40):
        if builder.done():
            break
        builder.tick(fill_running=False)
        time.sleep(0.005)
    if not builder.done():
        bad.append(f"the builder did not finish: {builder.published} segments "
                   f"published of {ROWS // CHUNK}")
    if builder.published != ROWS // CHUNK:
        bad.append(f"{builder.published} segments published, expected "
                   f"{ROWS // CHUNK}")
    if store.coverage.find(FORM.key(), table.pts_of(300)) is None:
        bad.append("a published segment is not in the record")
    if any(store.directory.joinpath("_staging").glob("seg-*.mp4")):
        bad.append("segments were left in staging")

    # a fill running takes the decoder: the proxy waits
    idle = ProxyBuilder(SpanStore(root / "proxy2", table), table, FORM.key(),
                        TouchLauncher(), segments=4, rows_per_segment=CHUNK)
    if idle.tick(fill_running=True):
        bad.append("the builder launched while a fill was running")
    run.note(f"redirect: {builder.published} segments published through a "
             f"touch launcher in {len(launcher.launched)} batches, none left "
             "in staging")
    store.close()
    return "redirect (far, and somewhere nearer)", 3, bad


def case_geometry(run: Run) -> tuple[str, int, list[str]]:
    """Does the recorded form describe the pixels ffmpeg actually writes?

    Found by driving the builder against real ffmpeg rather than by reasoning:
    the record said `1328x746` and the segments were `1328x748`. `scale=W:-2`
    rounds the free dimension to the *nearest* even number, and truncating to
    an even number instead is off by two often enough to matter. A store whose
    form key does not describe its frames is the failure the form vocabulary
    exists to prevent, and nothing notices until something compares the two.

    Checked as arithmetic against shapes whose answers are known, so it needs
    no ffmpeg — but it is here because a real run is what asked the question.
    """
    bad: list[str] = []
    cases = [
        # source w, h, target w -> what `scale=W:-2` writes
        ((5312, 2988), 1328, 748),   # the source in video-tests: 747 rounds up
        ((1920, 1080), 1280, 720),   # exact, and even either way
        ((1440, 1080), 640, 480),    # exact
        ((3840, 2160), 1000, 562),   # 562.5 rounds to 562
    ]
    for (width, height), target, expected in cases:
        shape = Shape(codec="hevc", width=width, height=height,
                      pix_fmt="yuv420p", average_rate=Fraction(24000, 1001),
                      timebase=Fraction(1, 24000))
        launcher = FFmpegLauncher(Path("x.mp4"), shape, 100, 96, width=target)
        got = launcher.output_size()
        if got != (target, expected):
            bad.append(f"{width}x{height} at width {target} sized {got}, "
                       f"ffmpeg writes ({target}, {expected})")
        truncated = int(height * target / width) // 2 * 2
        if truncated != expected and got[1] == truncated:
            bad.append(f"{width}x{height} used the truncating rule, which is "
                       f"{truncated} where ffmpeg writes {expected}")
        if launcher.form().out != got:
            bad.append("the launcher's form disagrees with its own output size")
    run.note("geometry: the launcher owns the rounding, so a caller cannot "
             "compute the form a second way and disagree silently")
    return "geometry (form matches the pixels)", len(cases), bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        frontier_mod.fill_order = from_the_start

    run = Run(
        experiment="P5-producers" + ("-broken" if broken else ""),
        question="Do the background producers work in the order they claim, "
                 "and can that order be read without watching a picture?",
    )
    run.note("no footage and no ffmpeg: the builder takes its launcher as an "
             "argument and the check hands it one that touches files")
    if broken:
        run.note("RUN WITH --broken: the fill is anchored on the window's "
                 "start rather than the playhead's chunk, which is what the "
                 "explorer did before the freeze finding. `order` and `fill` "
                 "are expected to FAIL.")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        results = [
            case_order(run),
            case_pieces(run),
            case_disk(run),
            case_fill(run, root),
            case_pause(run, root),
            case_batches(run),
            case_redirect(run, root),
            case_geometry(run),
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
