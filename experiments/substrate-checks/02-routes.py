"""Does every route return the same pixels, and say so when it has none?

P1 of `docs/archive/2026.08-substrate-port.md`. Two properties, and the second is the one
this tree's footage exists to break.

**Parity.** Every live route returns identical pixels for the same row of the
same file. If they did not, which decoder happened to be in position would reach
a stored value, and two runs of one analysis would disagree for a reason nothing
records. Routes may differ in what they *cost* — that is the entire subject of
`decode-experiments` — and may not differ in what they *say*.

**Absence.** A row present in the frame table can still decode to nothing. The
5.3K source was cut mid-GOP and its first twenty packets carry timestamps below
its stated start; asked for one of them, a route must report absent rather than
handing back the next image along. Every predecessor of this code matched a
frame within half a frame of the target and would have returned frame 20 for a
request for frame 0, silently, forever. That is the second half of ADR-0004's
three-different-counts, and P0 could not see it because a demux-only pass cannot.

Six cases.

**fake** — the route with no file behind it, checked first because everything
above this layer is going to be checked *through* it. A frame knows its own row,
an undecodable row reports absent and parks where a real decoder would, and the
record of what was asked is in the order it was asked.

**head** — the real thing: rows 0-19 absent, row 20 present, and row 20's image
not equal to whatever a tolerant matcher would have handed back for row 0.

**parity** — software against hardware against hybrid, same rows, byte for byte.
A machine with no hardware decoder runs the pair it has and says so in the notes
rather than passing quietly.

**keyframe** — `keyframe_at` lands on a row that is a keyframe and whose image
equals `at` of the same row. In the head it lands *after* the request, which is
the case a caller assuming otherwise gets wrong.

**probe** — against a redirected settings directory, so this never touches the
person's real verdicts: an empty cache races and writes, a second open reads and
does not re-race, and the numbers behind the verdict are recorded beside it.

**cost** — sequential stepping against random seeking, as timed cases. Not the
point of this file and not a threshold anything is held to (ADR-0008); recorded
because the numbers are free once the routes are open and a later measurement
should have something to sit beside.

`--broken` restores the half-frame tolerance that every predecessor carried:
a frame whose timestamp is merely near the target is accepted. `head` must fail
and `keyframe` may; parity will not notice, because both sides are equally
wrong, which is exactly why parity alone was never enough.

Run:
    uv run --group experiments python experiments/substrate-checks/02-routes.py
    uv run --group experiments python experiments/substrate-checks/02-routes.py --broken
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE, Run, report, time_case  # noqa: E402

from sieve.decode import fake as fake_mod  # noqa: E402
from sieve.decode import probe  # noqa: E402
from sieve.decode.fake import FakeRoute  # noqa: E402
from sieve.decode.hybrid import HybridRoute  # noqa: E402
from sieve.decode.pyav import PyAVRoute, hardware, software  # noqa: E402
from sieve.frame import FrameTable, Shape  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
HEAD = 20          #: what P0 measured: packets carrying a pts below the start
SAMPLE_ROWS = 24   #: rows compared per parity pair — each one is a real seek


def tolerant_at(self: PyAVRoute, row: int):
    """`at` as every predecessor wrote it: near enough is the match.

    Kept here rather than in `src/`, as the thing being argued against. The
    half-frame tolerance existed to absorb a timestamp that had been computed
    instead of looked up; with a frame table there is nothing to absorb, and
    what the tolerance actually does is answer a request for a frame that does
    not exist with the frame after it.
    """
    if not 0 <= row < len(self.table):
        raise IndexError(row)
    target = self.table.pts_of(row)
    step = self.table.pts_of(1) - self.table.pts_of(0)
    self.container.seek(target, stream=self.stream)
    self._decoded = self.container.decode(self.stream)
    for frame in self._decoded:
        if frame.pts is None:
            continue
        if frame.pts + step // 2 >= target:
            landed = self.table.row_of(int(frame.pts))
            self.pos = landed if landed is not None else row
            return self._image(frame), "seek (tolerant)"
    return None


def case_fake(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    table = fake_mod.table(600, head=HEAD)
    route = FakeRoute(table, undecodable=range(HEAD))

    for row in (HEAD, HEAD + 1, 300, 599):
        answer = route.at(row)
        if answer is None:
            bad.append(f"fake row {row} reported absent and should not have")
        elif FakeRoute.row_in(answer[0]) != row:
            bad.append(f"fake row {row} returned frame "
                       f"{FakeRoute.row_in(answer[0])}")

    for row in (0, 5, HEAD - 1):
        if route.at(row) is not None:
            bad.append(f"fake row {row} is undecodable and returned an image")
        elif route.pos != HEAD:
            bad.append(f"fake parked at {route.pos} after an absent row, "
                       f"not on the first decodable row {HEAD}")

    route.reset()
    wanted = [100, 101, 102, 400, 401]
    for row in wanted:
        route.at(row)
    if route.asked != wanted:
        bad.append(f"fake recorded {route.asked}, asked {wanted}")
    # 100 is a jump from the head, 400 is a jump from 102; the rest follow
    if (route.steps, route.seeks) != (3, 2):
        bad.append(f"fake counted {route.steps} steps and {route.seeks} seeks; "
                   "expected 3 and 2")
    run.note(f"fake: {len(table)} rows, {HEAD} undecodable, marker round-trip "
             "and request order both hold")
    return "fake (no footage)", len(table), bad


def case_head(run: Run, table: FrameTable, route) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    absent = [row for row in range(HEAD) if route.at(row) is None]
    run.note(f"head: {len(absent)} of the first {HEAD} rows reported absent")
    if len(absent) != HEAD:
        present = [row for row in range(HEAD) if row not in absent]
        bad.append(f"rows {present[:6]} decoded to an image; a demuxed packet "
                   "below the stated start should decode to nothing")

    first = route.at(HEAD)
    if first is None:
        bad.append(f"row {HEAD} reported absent; the head should end there")
        return "head (rows 0-19 absent)", HEAD + 1, bad

    # the failure a tolerant matcher produces is not "an error" but "a
    # plausible image", so the check is that the two requests differ
    for row in (0, 5):
        answer = route.at(row)
        if answer is not None and np.array_equal(answer[0], first[0]):
            bad.append(f"row {row} returned row {HEAD}'s image")
    return "head (rows 0-19 absent)", HEAD + 1, bad


def case_parity(run: Run, table: FrameTable, shape: Shape,
                routes: dict) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    names = list(routes)
    if len(names) < 2:
        run.note(f"parity: only {names} available on this machine, so nothing "
                 "was compared — this is a machine fact, not a pass")
        return "parity (route against route)", 0, bad

    rows = np.linspace(HEAD, len(table) - 1, SAMPLE_ROWS).astype(int).tolist()
    reference = names[0]
    compared = 0
    for row in rows:
        base = routes[reference].at(row)
        if base is None:
            bad.append(f"{reference} reported row {row} absent")
            continue
        for other in names[1:]:
            answer = routes[other].at(row)
            if answer is None:
                bad.append(f"{other} reported row {row} absent where "
                           f"{reference} did not")
            elif not np.array_equal(base[0], answer[0]):
                differing = int((base[0] != answer[0]).sum())
                bad.append(f"{other} differs from {reference} at row {row} in "
                           f"{differing} of {base[0].size} bytes")
            compared += 1
    run.note(f"parity: {compared} comparisons over {len(rows)} rows, "
             f"{' vs '.join(names)}")
    return "parity (route against route)", compared, bad


def case_keyframe(run: Run, table: FrameTable, route) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    rows = np.linspace(0, len(table) - 1, 40).astype(int).tolist()
    after_head = 0
    for row in rows:
        answer = route.keyframe_at(row)
        if answer is None:
            bad.append(f"keyframe_at({row}) found nothing")
            continue
        image, landed, _ = answer
        if landed > row:
            # the head: the keyframe at or before the request decodes to
            # nothing, so the first real image is *after* it and is not itself
            # a keyframe. Landing here is correct; landing here outside the
            # head would mean the seek overshot.
            after_head += 1
            if row >= HEAD:
                bad.append(f"keyframe_at({row}) landed ahead at {landed} "
                           "outside the head")
        elif not bool(table.keyframe[landed]):
            bad.append(f"keyframe_at({row}) landed on {landed}, not a keyframe")
        direct = route.at(landed)
        if direct is None:
            bad.append(f"row {landed} was reachable by keyframe and absent by "
                       "at()")
        elif not np.array_equal(direct[0], image):
            bad.append(f"keyframe_at({row}) and at({landed}) disagree")
    run.note(f"keyframe: {len(rows)} probes, {after_head} landed after the "
             "request — the head, where the keyframe before decodes to nothing")
    return "keyframe (lands where it says)", len(rows), bad


def case_probe(run: Run, table: FrameTable, shape: Shape) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["SIEVE_SETTINGS"] = str(Path(tmp) / "settings.json")
        try:
            if probe.get(shape.probe_key()) is not None:
                bad.append("a redirected probe directory was not empty")
            cold = HybridRoute(BIG, table, shape)
            verdict, measured = cold.verdict, dict(cold.measured_ms)
            cold.close()

            if cold.hw is None and not measured:
                run.note("probe: no hardware decoder on this machine, so the "
                         "race did not run and the verdict is sw by absence")
            else:
                if not measured:
                    bad.append("the race ran and recorded no measurements")
                stored = probe.get(shape.probe_key())
                if stored is None:
                    bad.append("the race ran and wrote no verdict")
                elif stored.get("verdict") != verdict:
                    bad.append(f"stored verdict {stored.get('verdict')} != "
                               f"{verdict}")
                run.note(f"probe: raced {measured}, verdict {verdict!r}, "
                         f"key {shape.probe_key()}")

            warm = HybridRoute(BIG, table, shape)
            if cold.hw is not None and not warm.from_cache:
                bad.append("a second open re-raced instead of reading the "
                           "verdict it had just written")
            if warm.verdict != verdict:
                bad.append(f"warm verdict {warm.verdict} != cold {verdict}")
            warm.close()
        finally:
            os.environ.pop("SIEVE_SETTINGS", None)
    return "probe (raced once, cached)", 1, bad


def case_cost(run: Run, table: FrameTable, route) -> None:
    """Numbers, recorded because they are free here and not because of a target."""
    def sequential():
        for row in range(1000, 1000 + 120):
            route.at(row)
            yield row

    def scattered():
        rows = np.linspace(HEAD, len(table) - 1, 30).astype(int)
        for row in rows:
            route.at(int(row))
            yield row

    report(time_case(run, "sequential (steps)", sequential,
                     params={"rows": 120}))
    report(time_case(run, "scattered (seeks)", scattered,
                     params={"rows": 30}, warmup=1))


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        PyAVRoute.at = tolerant_at

    run = Run(
        experiment="P1-routes" + ("-broken" if broken else ""),
        question="Do all routes return the same pixels, and does a row that "
                 "decodes to nothing report absent rather than the next frame?",
    )
    if broken:
        run.note("RUN WITH --broken: the exact pts match is replaced by the "
                 "half-frame tolerance every predecessor carried. `head` is "
                 "expected to FAIL; `parity` is not, because both sides are "
                 "equally wrong — which is why parity alone was never enough.")

    results = [case_fake(run)]

    if not BIG.exists():
        run.note(f"every footage case skipped: {BIG.name} absent")
    else:
        run.add_footage(BIG)
        table = FrameTable.cached(BIG)
        shape = Shape.read(BIG)
        routes: dict = {"software": software(BIG, table)}
        hw = hardware(BIG, table)
        if hw is not None:
            routes["hardware"] = hw
        hybrid = HybridRoute(BIG, table, shape)
        routes["hybrid"] = hybrid

        results.append(case_head(run, table, routes["software"]))
        results.append(case_parity(run, table, shape, routes))
        results.append(case_keyframe(run, table, routes["software"]))
        results.append(case_probe(run, table, shape))
        print("\ncost (recorded, not a threshold):")
        case_cost(run, table, routes["software"])
        print()
        for route in routes.values():
            route.close()

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
        print("the --broken run tripped nothing: either the head is not being "
              "reached or the tolerance is not being applied, and these cases "
              "are not demonstrating what they claim.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
