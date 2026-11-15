"""The documents lately opened or saved: their paths, each with when it was noted, a line a
document and newest first, in a file its caller names. FILE is the user's own, which the launcher
hands the window; a window handed none notes nothing."""
import os
import tempfile
import time


def app_folder():
    """Where the player keeps what outlives a launch: SIEVE under LOCALAPPDATA, else under the temp folder."""
    return os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "SIEVE")


FILE = os.path.join(app_folder(), "recent.txt")    # a line a document, newest first: when it was noted, a tab, its path
KEEP = 10


def _noted(file):
    try:
        with open(file, encoding="utf-8") as f:
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


def entries(file):
    """(path, when it was noted as time.time() gives it, or None for a line that says no time) for
    each path noted in `file` that is a file now, newest first; one whose file is away stays noted."""
    return [(p, when) for p, when in _noted(file) if os.path.isfile(p)]


def note(file, path):
    """Puts `path` first of at most KEEP in `file`, noted now; a list that will not write is left
    as it was, whole."""
    path = os.path.abspath(path)
    kept = [(path, time.time()), *((p, when) for p, when in _noted(file) if os.path.normcase(p) != os.path.normcase(path))][:KEEP]
    part = f"{file}.part"
    try:
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(part, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(f"{when:.0f}\t{p}\n" if when is not None else f"{p}\n" for p, when in kept))
        os.replace(part, file)
    except OSError:
        pass
