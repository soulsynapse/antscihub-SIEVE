"""A process that exits still holding a player exits cleanly.

The player's decode thread is stopped on two paths — `shutdown()`, which an
orderly exit calls, and the `destroyed` closure, which catches a player that is
simply dropped. Neither reaches a player that is *held*: an object still
referenced at interpreter exit is never destroyed, so `destroyed` never fires,
and a running `QThread` torn down by static destruction ends the process
abnormally. Nothing about that is visible from inside the session — every test
passes, no traceback is printed, and the only evidence is the exit code, which
is why a suite bisected by test selection cannot localise it.

Asserted from a subprocess because the claim is about how a process *ends*, and
a session cannot observe its own exit code — the same reason
`test_fixture_gate.py` reaches for one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

#: Holds the player in a list to interpreter exit, which is the shape a window
#: that outlives its last test has. It never opens a video: the thread starts in
#: `__init__`, so a bare construction is the whole of the hazard.
_HOLD_A_PLAYER = """
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from sieve.gui.transport.player import VideoPlayer

application = QApplication([])
kept = [VideoPlayer()]
application.processEvents()
"""


def test_a_process_holding_a_player_at_exit_exits_zero_and_silent() -> None:
    """Exit code and stderr both, because the two failures are separable.

    A thread left running takes the process down with a nonzero code and no
    output at all; a wrapper touched after Qt reaped it prints a `RuntimeError`
    from a slot and changes no exit code. A fix for one is not a fix for the
    other, and asserting on only the code would let the tracebacks come back.
    """
    completed = subprocess.run(
        [sys.executable, "-c", _HOLD_A_PLAYER],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert completed.returncode == 0, (
        f"exited {completed.returncode} holding a player; stderr: {completed.stderr[-2000:]}"
    )
    assert completed.stderr == "", completed.stderr[-2000:]
