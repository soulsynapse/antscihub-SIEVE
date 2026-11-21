"""The documents lately opened or saved: their paths, each with when it was noted, a line a
document and newest first, in a file its caller names. FILE is the user's own, which the launcher
hands the window; a window handed none notes nothing. Beside it, each document's last view: the
node selected and the window, kept apart from the document so moving them changes nothing saved."""
import json
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


def last(file):
    """The newest path noted in `file` that is a file now, or None."""
    return next((p for p, _ in entries(file)), None)


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


KEEP_VIEWS = 100


def views_beside(file):
    """The file beside `file` that keeps each document's last view."""
    return os.path.join(os.path.dirname(file), "views.json")


def _views(file):
    try:
        with open(file, encoding="utf-8") as f:
            views = json.load(f)
        return views if isinstance(views, dict) else {}
    except (OSError, ValueError):
        return {}


def view_of(file, path):
    """(the node selected, (first row, rows) of the window) as last kept in `file` for the document
    at `path`, each None where it was not kept; a view that will not read is none."""
    v = _views(file).get(os.path.normcase(os.path.abspath(path)))
    if not isinstance(v, dict):
        return None, None
    sel, win = v.get("selection"), v.get("window")
    ok = isinstance(win, list) and len(win) == 2 and all(isinstance(x, int) for x in win)
    return (sel if isinstance(sel, str) else None), (tuple(win) if ok else None)


def keep_view(file, path, selection, window):
    """Keeps in `file` the view of the document at `path`, the newest of at most KEEP_VIEWS; a file
    that will not write is left as it was, whole."""
    views = _views(file)
    key = os.path.normcase(os.path.abspath(path))
    views.pop(key, None)
    views[key] = {"selection": selection, "window": [int(window[0]), int(window[1])]}
    views = dict(list(views.items())[-KEEP_VIEWS:])
    part = f"{file}.part"
    try:
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(part, "w", encoding="utf-8", newline="\n") as f:
            json.dump(views, f, indent=1)
        os.replace(part, file)
    except OSError:
        pass
