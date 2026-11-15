"""The documents lately opened or saved: their paths in a file under the app folder, newest first,
which the File menu's Open Recent reads."""
import os

from .store import app_folder

FILE = os.path.join(app_folder(), "recent.txt")    # one path a line, newest first
KEEP = 10


def _noted():
    try:
        with open(FILE, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except OSError:
        return []


def paths():
    """The noted paths that are files now, newest first; one whose file is away stays noted."""
    return [p for p in _noted() if os.path.isfile(p)]


def note(path):
    """Puts `path` first of at most KEEP; a list that will not write is left as it was."""
    path = os.path.abspath(path)
    kept = [path, *(p for p in _noted() if os.path.normcase(p) != os.path.normcase(path))][:KEEP]
    try:
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        with open(FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(f"{p}\n" for p in kept))
    except OSError:
        pass
