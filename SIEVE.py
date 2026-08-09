"""Launch the SIEVE window from a fresh checkout: double-click this file, or
run it from any shell. Everything project-side still goes through uv, which
owns the interpreter and the environment — whatever Python opens this file is
only the messenger, so there is no venv to activate and no install step first.

`--project` rather than `--directory` or a chdir: the picker the window opens
on lists the projects in the current directory (gui/project_select.py), so a
launcher that moved the caller into the checkout would answer a question the
caller had already answered. Double-clicking still starts here, which is the
right list for a fresh checkout.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def _hold() -> None:
    """A double-click has no console to read from once this returns, so a
    failure holds the window open. A clean exit closes it."""
    try:
        input("Press Enter to close.")
    except EOFError:
        pass


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("SIEVE runs through uv, which is not on PATH.")
        print("Install it from https://docs.astral.sh/uv/ and run this again.")
        _hold()
        return 1
    checkout = Path(__file__).resolve().parent
    # `check=False` because the exit code is the whole of what this returns:
    # raising here would print a traceback over a GUI that has already said
    # whatever it had to say.
    code = subprocess.run(
        [uv, "run", "--project", str(checkout), "sieve-gui", *sys.argv[1:]], check=False
    ).returncode
    if code != 0:
        _hold()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
