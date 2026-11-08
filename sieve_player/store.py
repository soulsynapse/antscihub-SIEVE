"""The store: the folder bakes land in, each a file named by its node's key with a sidecar beside it
that says what the file is, the rule for where the folder is, and which kinds have a writer. The
window shows what `status()` says and `choose()`s on the user's behalf, a bake writes through
`writer()`, `place()` and `write_sidecar()`, and a reader asks `sidecar()`."""
import json
import os
import shutil
import subprocess
import tempfile
import time

STORE_ENV = "SIEVE_STORE"       # the store's folder when none is chosen; unset: `store` under app_folder()
SIDECAR = ".sieve.json"
FIELDS = ("key", "kind", "document", "node", "rows", "increment", "fps", "written_fps", "shape", "quality", "commit",
          "written")


def app_folder():
    """Where the player keeps what outlives a launch: SIEVE under LOCALAPPDATA, else under the temp folder."""
    return os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "SIEVE")


CHOICE = os.path.join(app_folder(), "store.txt")    # holds the folder the user chose, one line


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


def writable(path):
    """"" when a file can be written under `path`, creating the folder if it is not there; else why not."""
    try:
        os.makedirs(path, exist_ok=True)
        fd, probe = tempfile.mkstemp(dir=path)
        os.close(fd)
        os.remove(probe)
    except OSError as e:
        return f"{path} cannot be written: {e.strerror or e}"
    return ""


def choose(path):
    """Makes `path` the store, remembered across launches, and returns ""; a folder that cannot be
    written is refused with the reason and the choice stands as it was."""
    path = os.path.abspath(path)
    why = writable(path)
    if why:
        return why
    os.makedirs(os.path.dirname(CHOICE), exist_ok=True)
    with open(CHOICE, "w", encoding="utf-8") as f:
        f.write(path + "\n")
    return ""


def held(path=None):
    """The bytes the store's files take, sidecars included; 0 for a folder that is not there."""
    path = path or folder()
    try:
        with os.scandir(path) as it:
            return sum(e.stat().st_size for e in it if e.is_file())
    except OSError:
        return 0


def status(path=None):
    """(folder, bytes held, bytes the disk has free, reason): what the player shows of the store.
    `reason` is "" when the folder can be written, else why not, and free is 0 then."""
    path = path or folder()
    why = writable(path)
    free = 0 if why else shutil.disk_usage(path).free
    return path, held(path), free, why


def writer(kind):
    """(the file's extension, the writer class) for `kind`, or None for a kind no bake can write."""
    from .writers import WRITERS
    return WRITERS.get(kind)


def kinds():
    """The kinds a bake can write, sorted."""
    from .writers import WRITERS
    return sorted(WRITERS)


def place(key, ext, path=None):
    """Where the file baked under `key` lives: `key` with `ext`, its extension with the dot, in the store."""
    return os.path.join(path or folder(), key + ext)


def sidecar_path(key, path=None):
    return os.path.join(path or folder(), key + SIDECAR)


def write_sidecar(key, path=None, **fields):
    """Writes the sidecar for `key`, whole or not at all, from `fields`, which must name every one
    of FIELDS but `key`, `commit` and `written`, filled in here when not given. Returns what it wrote."""
    missing = set(FIELDS) - {"key", "commit", "written"} - set(fields)
    if missing or set(fields) - set(FIELDS):
        raise ValueError(f"a sidecar has {FIELDS}; missing {sorted(missing)}, unknown {sorted(set(fields) - set(FIELDS))}")
    d = {"key": key, **fields}
    d.setdefault("commit", commit())
    d.setdefault("written", time.strftime("%Y-%m-%dT%H:%M:%S"))
    d = {k: d[k] for k in FIELDS}
    target = sidecar_path(key, path)
    part = target + ".part"
    try:
        with open(part, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
            f.write("\n")
        os.replace(part, target)
    except OSError:
        if os.path.exists(part):
            os.remove(part)
        raise
    return d


def sidecar(key, path=None):
    """The sidecar's fields for `key`, or None when the store has none for it; a sidecar is what makes a file ours."""
    try:
        with open(sidecar_path(key, path), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def commit():
    """The repository commit this code runs under, or "" when it is not a checkout or git is not there."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=os.path.dirname(os.path.abspath(__file__)),
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def fmt_bytes(n):
    """`n` bytes as the shortest figure to one decimal in B, KB, MB, GB or TB."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
