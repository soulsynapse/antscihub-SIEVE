"""Can a number box be corrected without arguing back?

The one property that makes `primitives/number.py` a primitive rather than a
widget somebody wrote for the crop card. Everything it edits is a *clamped*
quantity — a crop corner that must stay on the frame, a budget that must stay
positive — and every such editor has the same shape: a person pushes a value,
something decides what is actually allowed, and the box must end up showing
that.

**The failure is a loop, and it is silent.** If a box announces a correction the
same way it announces a keystroke, its owner is asked to decide again about a
value it has just decided. Where the owner's clamp is idempotent the second pass
agrees and it stops; where it is not, the two trade the value back and forth for
as long as they disagree, and what a person sees is a field that will not take
what they typed. Nothing raises. `show_value` not emitting takes the whole class
off the table instead of relying on every clamp anybody ever writes to
terminate.

Four cases, offscreen: a signal is not about pixels.

**quiet** — `show_value` changes the value and says nothing; a person's edit
says something. This is the case `--broken` fails.

**settles** — a box wired to a clamp that *disagrees with itself* — one that
moves a value it has already approved — still comes to rest, because the
correction is silent. Driven against a deliberately non-idempotent clamp, since
an idempotent one would settle either way and prove nothing.

**typing** — the value is not announced letter by letter. Typing `1024` passes
through 1, 10 and 102, and a clamp reading those would fight the person typing
them.

**wheel** — a box without focus ignores the wheel, so scrolling a column of them
does not change the one the pointer crosses.

`--broken` makes `show_value` announce, which is what `setValue` alone does and
what a box written without this property would do.

Run:
    uv run --group experiments python experiments/substrate-checks/15-numberbox.py
    uv run --group experiments python experiments/substrate-checks/15-numberbox.py --broken
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.gui.primitives import number as number_mod  # noqa: E402
from sieve.gui.primitives.number import NumberBox  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

#: how many pushes count as "will not settle" before the case gives up
PATIENCE = 40


def loud_show(self, value: int) -> None:
    """`show_value` that announces, which is `setValue` with extra steps.

    Kept here as the thing being argued against. It is what a box written
    without this property does, and it looks harmless: the value changed, so
    say so.
    """
    self.setValue(value)


def case_quiet(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    box = NumberBox(100, low=0, high=5312, step=2)
    heard: list[int] = []
    box.chosen.connect(heard.append)

    box.show_value(512)
    if box.value() != 512:
        bad.append(f"show_value(512) left the box at {box.value()}")
    if heard:
        bad.append(f"show_value announced {heard}; a correction is not a "
                   "person's doing and must not be reported as one")

    box.setValue(64)          # what a person's editing goes through
    if heard != [64]:
        bad.append(f"a person's edit announced {heard}, expected [64]")

    box.show_value(64)        # no change at all
    if heard != [64]:
        bad.append("showing the value already up announced something")
    run.note(f"quiet: show_value moved the box and said nothing; an edit said "
             f"{heard}")
    return "quiet (told, not asked)", 3, bad


def case_settles(run: Run, app) -> tuple[str, int, list[str]]:
    """A clamp that argues with itself, and a box that lets it stop."""
    bad: list[str] = []
    box = NumberBox(0, low=0, high=1000)
    pushes: list[int] = []

    def owner(value: int) -> None:
        # deliberately not idempotent: it moves a value it has already
        # approved. An idempotent clamp settles whatever the box does, so it
        # would demonstrate nothing about the box.
        pushes.append(value)
        if len(pushes) > PATIENCE:
            return
        box.show_value(500 if value != 500 else 501)

    box.chosen.connect(owner)
    box.setValue(42)
    if len(pushes) > 1:
        bad.append(f"a disagreeing clamp was consulted {len(pushes)} times for "
                   "one edit; the box is announcing its own corrections")
    if box.value() != 500:
        bad.append(f"the box came to rest at {box.value()}, not where its "
                   "owner put it")
    run.note(f"settles: a clamp that moves its own approved value was asked "
             f"{len(pushes)} time(s) and the box rests at {box.value()}")
    return "settles (against a clamp that argues)", 1, bad


def case_typing(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    box = NumberBox(0, low=0, high=5312)
    if box.keyboardTracking():
        bad.append("keyboard tracking is on, so 1024 is announced as 1, then "
                   "10, then 102, and a clamp fights the person typing")
    heard: list[int] = []
    box.chosen.connect(heard.append)
    box.lineEdit().setText("1024")     # mid-edit, nothing committed
    if heard:
        bad.append(f"typing announced {heard} before the edit finished")
    box.interpretText()                # what leaving the field does
    if heard != [1024]:
        bad.append(f"finishing the edit announced {heard}, expected [1024]")
    run.note("typing: nothing is announced until the edit finishes, so a "
             "clamp never sees a half-typed number")
    return "typing (whole numbers, not prefixes)", 2, bad


def case_wheel(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    box = NumberBox(100, low=0, high=1000)
    heard: list[int] = []
    box.chosen.connect(heard.append)

    def roll():
        return QWheelEvent(
            QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, 120),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False)

    box.clearFocus()
    app.sendEvent(box, roll())
    if box.value() != 100 or heard:
        bad.append(f"a box without focus took the wheel: {box.value()}, "
                   f"heard {heard}")
    run.note("wheel: ignored without focus, so scrolling a column of these "
             "does not change the one the pointer crosses")
    return "wheel (only when it is the one in use)", 1, bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        number_mod.NumberBox.show_value = loud_show

    app = QApplication.instance() or QApplication([])
    run = Run(
        experiment="T1-numberbox" + ("-broken" if broken else ""),
        question="Can a number box be handed a correction without asking its "
                 "owner to decide again?",
    )
    run.note("offscreen: a signal is not about pixels")
    if broken:
        run.note("RUN WITH --broken: `show_value` announces, which is what a "
                 "box written without this property does. `quiet` and "
                 "`settles` are expected to FAIL.")

    results = [
        case_quiet(run, app),
        case_settles(run, app),
        case_typing(run, app),
        case_wheel(run, app),
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
