"""Does the record say what it knows, and admit what it does not?

P3 of `docs/substrate/port-plan.md`. Two records, one property each, and the
property is the same shape both times: **absence is a state, not a value.**

For a series, the failure is a row that was never written reading as a
legitimate zero. Nothing detects it downstream — a mean over a stretch that is
half-unwritten is a number, plausible, and wrong — and every consumer added
later is one that did not know to check. So `get` returns `None` and coverage is
its own array.

For a ledger, the failure is an interval whose time is not fully accounted for
being reported as though it were. ADR-0008 is explicit that unattributed time is
not by itself waste: it may be time that bought something nobody has
instrumented yet, and a driven session of the tool explorer was diagnosed three
times against the instruments that existed before the remainder revealed the
largest term had no clock on it at all. So the account closes against the
interval that actually elapsed and the remainder is reported rather than
absorbed.

Seven cases, none needing footage.

**coverage** — an unwritten row is `None`; a row written as zero is `0.0`; runs
and missing agree with what was put. This is the one `--broken` fails.

**honest** — a step whose oldest input sits *k* rows back has no honest value
for the first *k* rows of a run, and `first_honest` names the boundary so that
producers do not each derive it privately and one of them differently.

**snapshot** — a reader gets copies, not views. A numpy slice of a buffer
another thread is writing is a race whose symptom is a plausible number rather
than a crash, so the check mutates the series after taking a snapshot and
requires the snapshot not to have moved.

**sidecar** — a series round-trips through save and load with its identity taken
from the sidecar, and two keys that differ cannot land on one file. The second
half found a real defect: the original stem substituted offending characters out
of the key, which is many-to-one, so two keys differing only where it mapped
wrote to one file and the second destroyed the first — leaving the sidecar
honestly describing the survivor, so nothing afterwards was detectably wrong.

**account** — the clocks sum to what is attributed and the remainder is the
interval minus that, closed against elapsed time. Also that `account` has no
parameter for what the interval *should* have been: ADR-0008's refusal of a
budget is meant to be structural, and a ledger that could be asked whether it
was inside one would be asked it.

**separation** — waste and a deliberate discard cannot be recorded through one
another, and waste without an address is refused. A count nobody can act on is
a count everybody learns to ignore.

**decimation** — steady play is kept one in eight and the drops are counted, so
the true rate is recoverable from a record that did not keep every row. The
second thing `--broken` fails.

`--broken` makes `Series.get` return the stored float without consulting
coverage, and `Ledger.serve` drop rows without counting them. Both are the
tidier-looking version of the code, which is the point.

Run:
    uv run --group experiments python experiments/substrate-checks/04-record.py
    uv run --group experiments python experiments/substrate-checks/04-record.py --broken
"""

from __future__ import annotations

import inspect
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.analysis.series import Series  # noqa: E402
from sieve.session import ledger as ledger_mod  # noqa: E402
from sieve.session.ledger import (  # noqa: E402
    CHOSEN_KINDS,
    PLACEHOLDER,
    PREDICTED_FETCH,
    WASTE_KINDS,
    Ledger,
)

harness.RESULTS = Path(__file__).resolve().parent / "results"

ROWS = 400
STEP = 1001
#: a form key as `frame.form` actually spells one, with the `+`, `@` and `:`
#: that make it unfit for a filename on at least one platform
FORM_KEY = "2144+982+1024x1024@1024x1024:gray"


def blank(rows: int = ROWS) -> Series:
    return Series(source="GX010047.MP4", tool_key="dis(preset=ultrafast)",
                  form_key=FORM_KEY,
                  pts=np.arange(rows, dtype=np.int64) * STEP,
                  timebase="1/24000")


def loose_get(self: Series, row: int):
    """`get` without the coverage check — the tidier-looking version.

    Kept here as the thing being argued against. It is one line shorter, it
    never returns `None` so no caller needs a branch, and it makes an unwritten
    row indistinguishable from a row whose value is genuinely zero.
    """
    with self.lock:
        if 0 <= row < len(self.values):
            return float(self.values[row])
    return None


def uncounted_serve(self: Ledger, task: str, tier: str, ms: float,
                    row: int | None = None) -> None:
    """Decimation that forgets what it dropped."""
    with self._lock:
        self.serves_seen += 1
        if task == "play" and self.decimate > 1:
            self._since_kept[tier] += 1
            if self._since_kept[tier] < self.decimate:
                return                       # dropped, and not counted
            self._since_kept[tier] = 0
        self._serves.append(ledger_mod.Serve(
            at_s=self.elapsed_s(), task=task, tier=tier, ms=ms, row=row,
            stands_for=1))                   # and standing for nothing


def case_coverage(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    series = blank()
    written = {10: 1.5, 11: 0.0, 12: -2.25, 50: 9.0}
    for row, value in written.items():
        series.put(row, value)

    for row, value in written.items():
        got = series.get(row)
        if got is None:
            bad.append(f"row {row} was written and reads absent")
        elif got != value:
            bad.append(f"row {row} was written {value} and reads {got}")

    # the whole point: a row that was never written, beside one written zero
    for row in (0, 9, 13, 399):
        if series.get(row) is not None:
            bad.append(f"row {row} was never written and reads "
                       f"{series.get(row)}")
    if series.get(11) != 0.0:
        bad.append("a row genuinely written as zero does not read as zero")

    runs = series.runs(0, ROWS)
    if runs != [(10, 13), (50, 51)]:
        bad.append(f"runs said {runs}")
    missing = series.missing(0, 20)
    if missing != [(0, 10), (13, 20)]:
        bad.append(f"missing said {missing}")
    fraction = series.coverage(0, 100)
    if abs(fraction - 0.04) > 1e-9:
        bad.append(f"coverage(0, 100) said {fraction}")
    run.note("coverage: an unwritten row is None and a written zero is 0.0 — "
             "the two the values array cannot tell apart")
    return "coverage (absence is not zero)", ROWS, bad


def case_honest(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    series = blank()
    for start, reach in ((0, 0), (0, 30), (100, 30), (100, 1)):
        boundary = series.first_honest(start, reach)
        if boundary != start + reach:
            bad.append(f"first_honest({start}, {reach}) said {boundary}")
    if series.first_honest(100, -5) != 100:
        bad.append("a negative reach moved the boundary backwards")
    run.note("honest: the boundary is asked for rather than derived by each "
             "producer, so two of them cannot disagree about which rows a run "
             "may vouch for")
    return "honest (warm-up boundary)", 5, bad


def case_snapshot(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    series = blank()
    for row in range(20, 40):
        series.put(row, float(row))
    values, covered = series.snapshot(20, 40)

    for row in range(20, 40):
        series.put(row, -1.0)
    if values[0] != 20.0:
        bad.append("a snapshot moved when the series was written afterwards; "
                   "it is a view, not a copy")
    if not covered.all():
        bad.append("a snapshot's coverage moved after the fact")
    if np.shares_memory(values, series.values):
        bad.append("the snapshot shares memory with the series")
    run.note("snapshot: copies, so a reader cannot see values and coverage "
             "from two different instants")
    return "snapshot (copies, not views)", 20, bad


def case_sidecar(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    series = blank()
    for row in range(5, 25):
        series.put(row, float(row) / 2)
    with tempfile.TemporaryDirectory() as tmp:
        path = series.save(Path(tmp))
        back = Series.load(path)
        if back.key != series.key:
            bad.append(f"key came back as {back.key!r}, not {series.key!r}")
        if back.form_key != FORM_KEY:
            bad.append("the form key did not survive the round trip")
        if back.timebase != series.timebase:
            bad.append("the timebase did not survive")
        if not np.array_equal(back.pts, series.pts):
            bad.append("the pts table did not survive")
        for row in (4, 5, 24, 25):
            if back.get(row) != series.get(row):
                bad.append(f"row {row} differs after a round trip")
        # the property that matters is not which characters survive but
        # whether two keys can land on one file. Substituting offending
        # characters out is many-to-one, so these two differ only where the
        # substitution maps — and the loser is destroyed silently, with the
        # sidecar left honestly describing the survivor.
        collide_a = blank(10)
        collide_b = blank(10)
        collide_a.form_key, collide_b.form_key = "a|b", "a__b"
        collide_a.put(0, 111.0)
        collide_b.put(0, 222.0)
        path_a, path_b = collide_a.save(Path(tmp)), collide_b.save(Path(tmp))
        if path_a == path_b:
            bad.append(f"two keys ({collide_a.key!r} and {collide_b.key!r}) "
                       "wrote to one file; the second destroyed the first")
        elif Series.load(path_a).get(0) != 111.0:
            bad.append("a series was overwritten by one with a different key")
    run.note(f"sidecar: a form key spelled {FORM_KEY!r} survives a round trip "
             "through a filename that could not have held it")
    return "sidecar (identity is not the path)", 4, bad


def case_account(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    book = Ledger()
    book.charge("serve", 4.0)
    book.charge("field", 3.5)
    book.charge("paint", 2.0)

    account = book.account(20.0, "serve", "field", "paint")
    if abs(account.attributed_ms - 9.5) > 1e-9:
        bad.append(f"attributed {account.attributed_ms}, expected 9.5")
    if abs(account.unattributed_ms - 10.5) > 1e-9:
        bad.append(f"unattributed {account.unattributed_ms}, expected 10.5")
    if abs(account.unattributed_share - 0.525) > 1e-9:
        bad.append(f"share {account.unattributed_share}")

    # attributed beyond the interval: the remainder floors rather than going
    # negative, because a negative remainder is a clock double-counting and
    # not a fact about the interval
    if book.account(5.0, "serve", "field", "paint").unattributed_ms != 0.0:
        bad.append("an over-attributed interval produced a negative remainder")

    with book.clock("measured"):
        total = sum(i * i for i in range(20_000))
    if book.account(1e6, "measured").clocks_ms["measured"] <= 0:
        bad.append(f"a context-managed clock recorded nothing ({total})")

    # ADR-0008 structurally: nothing here may be asked whether it is inside
    # a budget, so nothing here has a parameter for one
    names = list(inspect.signature(Ledger.account).parameters)
    offending = [n for n in names
                 if any(word in n.lower()
                        for word in ("target", "budget", "limit", "expected"))]
    if offending:
        bad.append(f"account() takes {offending}; the refusal of a budget is "
                   "meant to be structural, not a convention")
    run.note(f"account: closed against elapsed time, parameters {names} — no "
             "argument for what the interval should have been")
    return "account (closed against elapsed)", 4, bad


def case_separation(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    book = Ledger()
    book.waste(PREDICTED_FETCH, "row 412, crop form, declared by dis")
    book.chosen(PLACEHOLDER)
    book.chosen(PLACEHOLDER)

    counts = book.counts()
    if counts["waste"].get(PREDICTED_FETCH) != 1:
        bad.append(f"waste counted {counts['waste']}")
    if counts["chosen"].get(PLACEHOLDER) != 2:
        bad.append(f"chosen counted {counts['chosen']}")
    if book.waste_total() != 1:
        bad.append("a deliberate discard reached the waste total")

    for kind in CHOSEN_KINDS:
        try:
            book.waste(kind, "somewhere")
            bad.append(f"a chosen-discard kind {kind!r} was accepted as waste")
        except ValueError:
            pass
    for kind in WASTE_KINDS:
        try:
            book.chosen(kind)
            bad.append(f"a waste kind {kind!r} was accepted as a chosen "
                       "discard")
        except ValueError:
            pass
    try:
        book.waste(PREDICTED_FETCH, "")
        bad.append("waste without an address was accepted")
    except ValueError:
        pass
    run.note("separation: the two counts cannot be reached through one "
             "another, so filing one as the other takes a decision")
    return "separation (waste is not a cost)", len(WASTE_KINDS) + len(CHOSEN_KINDS), bad


def case_decimation(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    book = Ledger(decimate=8)
    plays = 800
    for row in range(plays):
        book.serve("play", "hit", 0.01, row=row)
    for row in range(10):
        book.serve("drag", "near", 6.0, row=row)

    kept = book.serves()
    play_rows = [s for s in kept if s.task == "play"]
    drag_rows = [s for s in kept if s.task == "drag"]

    if len(drag_rows) != 10:
        bad.append(f"{len(drag_rows)} of 10 drags kept; anything that is not "
                   "steady play should be kept whole")
    if not 90 <= len(play_rows) <= 110:
        bad.append(f"{len(play_rows)} play rows kept from {plays} at 1-in-8")
    if book.serves_seen != plays + 10:
        bad.append(f"serves_seen {book.serves_seen}, expected {plays + 10}")
    if book.serves_seen - book.serves_dropped != len(kept):
        bad.append(f"seen {book.serves_seen} minus dropped "
                   f"{book.serves_dropped} is not the {len(kept)} kept")

    represented = sum(s.stands_for for s in play_rows)
    if abs(represented - plays) > book.decimate:
        bad.append(f"kept rows stand for {represented} plays, not {plays}; "
                   "the true rate is not recoverable from the record")
    run.note(f"decimation: {plays} play serves kept as {len(play_rows)} rows "
             f"standing for {represented}, {book.serves_dropped} dropped and "
             "counted")
    return "decimation (drops, and says how many)", plays + 10, bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        Series.get = loose_get
        Ledger.serve = uncounted_serve

    run = Run(
        experiment="P3-record" + ("-broken" if broken else ""),
        question="Does a series distinguish an unwritten row from a zero, and "
                 "does a ledger report the time it cannot account for?",
    )
    run.note("no footage: both records are about bookkeeping, and neither has "
             "anything to do with pixels")
    if broken:
        run.note("RUN WITH --broken: `Series.get` ignores coverage and "
                 "`Ledger.serve` drops without counting. `coverage` and "
                 "`decimation` are expected to FAIL.")

    results = [
        case_coverage(run),
        case_honest(run),
        case_snapshot(run),
        case_sidecar(run),
        case_account(run),
        case_separation(run),
        case_decimation(run),
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
        print("the --broken run tripped nothing: the substitutions are not "
              "being reached and these cases are not demonstrating what they "
              "claim.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
