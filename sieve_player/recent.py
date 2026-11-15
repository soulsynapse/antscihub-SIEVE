"""The documents lately opened or saved: their paths, each with when it was noted, in a file under
the app folder, newest first, which the File menu's Open Recent reads."""
import os
import time

from .store import app_folder

FILE = os.path.join(app_folder(), "recent.txt")    # a line a document, newest first: when it was noted, a tab, its path
KEEP = 10


def _noted():
    try:
        with open(FILE, encoding="utf-8") as f:
            lines = [line.strip("\r\n") for line in f if line.strip()]
    except OSError:
        return []
    out = []
    for line in lines:
        when, tab, path = line.partition("\t")
        try:
            out.append((path, float(when)) if tab else (line, None))
        except ValueError:
            out.append((path, None))
    return out


def entries():
    """(path, when it was noted as time.time() gives it, or None for a line that says no time) for
    each noted path that is a file now, newest first; one whose file is away stays noted."""
    return [(p, when) for p, when in _noted() if os.path.isfile(p)]


def paths():
    return [p for p, _ in entries()]


def note(path):
    """Puts `path` first of at most KEEP, noted now; a list that will not write is left as it was."""
    path = os.path.abspath(path)
    kept = [(path, time.time()), *((p, when) for p, when in _noted() if os.path.normcase(p) != os.path.normcase(path))][:KEEP]
    try:
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        with open(FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(f"{when:.0f}\t{p}\n" if when is not None else f"{p}\n" for p, when in kept))
    except OSError:
        pass
