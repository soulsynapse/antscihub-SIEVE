"""The store: the one folder the files tools write of a video's footage land in, wherever the video
lies. This module resolves which folder it is, `folder()`, chosen else SIEVE_STORE else the default,
`choose()`s on the user's behalf, and reads what a folder holds for whoever draws it. What a file in
it is named, and what is in one, is its writer's: a tool's (tools/_cutfile.py), and the decoder's,
whose tables of frame times lie in one folder of it (decoder.TIMES_DIR). Imports no Qt.
"""
import os
import shutil
import tempfile

from .recent import app_folder

STORE_ENV = "SIEVE_STORE"       # the store's folder when none is chosen; unset: `store` under app_folder()
CHOICE = os.path.join(app_folder(), "store.txt")    # holds the folder the user chose, one line
PART = ".part"                  # in the name of a file not yet whole


def chosen():
    """The folder the user chose, or None while none is."""
    try:
        with open(CHOICE, encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def folder():
    """The store's folder: chosen, else STORE_ENV, else the default; nothing here creates it."""
    return chosen() or os.environ.get(STORE_ENV) or os.path.join(app_folder(), "store")


def probe(folder):
    """"" when a file can be written in `folder`, creating it if it is not there; else why not."""
    try:
        os.makedirs(folder, exist_ok=True)
        fd, made = tempfile.mkstemp(dir=folder)
        os.close(fd)
        os.remove(made)
    except OSError as e:
        return f"{folder} cannot be written: {e.strerror or e}"
    return ""


def choose(path):
    """Makes `path` the store, remembered across launches, and returns ""; a folder that cannot be
    written is refused with the reason and the choice stands as it was. What the store before it
    holds stays there."""
    path = os.path.abspath(path)
    why = probe(path)
    if why:
        return why
    os.makedirs(os.path.dirname(CHOICE), exist_ok=True)
    with open(CHOICE, "w", encoding="utf-8", newline="\n") as f:
        f.write(path + "\n")
    return ""


def held(folder):
    """(bytes, part files, their bytes) of every file under `folder`, the part files, what a writer
    that died with its process left, counted in the first too; zeros for a folder that is not there."""
    total = parts = part_bytes = 0
    for root, _, names in os.walk(folder):
        for name in names:
            try:
                n = os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
            total += n
            if PART in name:
                parts, part_bytes = parts + 1, part_bytes + n
    return total, parts, part_bytes


def disk(folder):
    """(bytes in all, bytes free) of the disk `folder` is, or would be, on: asked of the nearest
    folder up from it that exists; (0, 0) when none can be asked."""
    path = os.path.abspath(folder)
    while not os.path.isdir(path):
        up = os.path.dirname(path)
        if up == path:
            return 0, 0
        path = up
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return 0, 0
    return usage.total, usage.free
