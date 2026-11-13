"""The store: the folder bakes land in, each a file named by its node's key with a Sidecar beside it
that says what the file is. `Store` is one such folder as a value, what the worker writes through
and a document is checked against; the module resolves which folder is current, `folder()`, chosen
else SIEVE_STORE else the default, and `choose()`s on the user's behalf. Which kinds have a writer
is `writer()` and `kinds()`, the same whatever the folder."""
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, fields, replace

from .document import Bake, served
from .writers import PART, WRITERS, is_series, reader

STORE_ENV = "SIEVE_STORE"       # the store's folder when none is chosen; unset: `store` under app_folder()
SIDECAR = ".sieve.json"


@dataclass(frozen=True)
class Sidecar:
    """What makes a file in the store ours: everything a bake was written under. `rows` is (first,
    last) of the plate, `shape` the plane's or [] for a series kind; `commit` and `written` are
    filled in by `Store.write_sidecar` when left empty."""
    key: str
    kind: str
    document: str
    node: str
    rows: list
    increment: int
    fps: float
    written_fps: float
    shape: list
    quality: str
    commit: str = ""
    written: str = ""

    def bake(self, count):
        """The Bake a node saves to serve this file, over a plate of `count` rows."""
        return Bake(self.key, self.kind, is_series(self.kind), tuple(self.rows), self.increment, self.fps, self.written_fps,
                    tuple(self.shape), count)


FIELDS = tuple(f.name for f in fields(Sidecar))


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


def current():
    """The Store on `folder()`."""
    return Store(folder())


def choose(path):
    """Makes `path` the store, remembered across launches, and returns ""; a folder that cannot be
    written is refused with the reason and the choice stands as it was."""
    path = os.path.abspath(path)
    why = Store(path).probe()
    if why:
        return why
    os.makedirs(os.path.dirname(CHOICE), exist_ok=True)
    with open(CHOICE, "w", encoding="utf-8") as f:
        f.write(path + "\n")
    return ""


def writer(kind):
    """(the file's extension, the writer class) for `kind`, or None for a kind no bake can write."""
    return WRITERS.get(kind)


def kinds():
    """The kinds a bake can write, sorted."""
    return sorted(WRITERS)


@dataclass(frozen=True)
class Store:
    """One folder bakes land in. Reading it, `status`, `held`, `strays`, `free`, `sidecar`,
    `absent`, `missing` and `open_bake`, touches nothing on disk; `probe` and `write_sidecar` write,
    and a writer opened at `place` lands its file there."""
    folder: str

    def place(self, key, ext):
        """Where the file baked under `key` lives: `key` with `ext`, its extension with the dot."""
        return os.path.join(self.folder, key + ext)

    def sidecar_path(self, key):
        return os.path.join(self.folder, key + SIDECAR)

    def probe(self):
        """"" when a file can be written in the folder, creating it if it is not there; else why not."""
        try:
            os.makedirs(self.folder, exist_ok=True)
            fd, probe = tempfile.mkstemp(dir=self.folder)
            os.close(fd)
            os.remove(probe)
        except OSError as e:
            return f"{self.folder} cannot be written: {e.strerror or e}"
        return ""

    def held(self):
        """The bytes the folder's files take, sidecars included; 0 for a folder that is not there."""
        try:
            with os.scandir(self.folder) as it:
                return sum(e.stat().st_size for e in it if e.is_file())
        except OSError:
            return 0

    def strays(self):
        """(count, bytes) of the part files in the folder: what a bake that died with its process
        left, since a writer removes its own part on any failure it lives to see. Counted in `held()` too."""
        try:
            with os.scandir(self.folder) as it:
                parts = [e.stat().st_size for e in it if e.is_file() and PART in e.name]
        except OSError:
            return 0, 0
        return len(parts), sum(parts)

    def free(self):
        """The bytes free on the disk the folder is, or would be, on: asked of the nearest folder
        up from it that exists; 0 when none can be asked."""
        path = os.path.abspath(self.folder)
        while not os.path.isdir(path):
            up = os.path.dirname(path)
            if up == path:
                return 0
            path = up
        try:
            return shutil.disk_usage(path).free
        except OSError:
            return 0

    def status(self):
        """(bytes held, bytes free): what the player shows of the store. Whether it can be written
        is `probe()`'s to say, since answering that writes."""
        return self.held(), self.free()

    def absent(self, bake):
        """Why `bake`, a node's saved Bake, cannot be read from here, or "" when its file is there."""
        w = writer(bake.kind)
        if w is None:
            return f"no reader for a {bake.kind} bake"
        if not os.path.exists(self.place(bake.key, w[0])):
            return f"bake {bake.key} is not in the store at {self.folder}"
        return ""

    def missing(self, doc):
        """{node id: why} for every node of `doc` serving a bake this store cannot read: what whoever
        opens the document asks, so a node whose file is gone can be set live with the reason said."""
        out = {}
        for n in doc.nodes:
            b = served(n)
            if b is not None and (why := self.absent(b)):
                out[n.id] = f"{why}; serving live"
        return out

    def open_bake(self, bake, cache_bytes=0):
        """What reads `bake`, a node's saved Bake, back: IOError when it cannot be read."""
        why = self.absent(bake)
        if why:
            raise IOError(why)
        return reader(self.place(bake.key, writer(bake.kind)[0]), bake.kind, cache_bytes, bake.shape)

    def write_sidecar(self, side):
        """Writes `side`, a Sidecar, beside its file, whole or not at all, with the commit and the
        time filled in where it left them empty. Returns what it wrote."""
        side = replace(side, commit=side.commit or commit(), written=side.written or time.strftime("%Y-%m-%dT%H:%M:%S"))
        target = self.sidecar_path(side.key)
        part = target + PART
        try:
            with open(part, "w", encoding="utf-8") as f:
                json.dump(asdict(side), f, indent=2)
                f.write("\n")
            os.replace(part, target)
        except OSError:
            if os.path.exists(part):
                os.remove(part)
            raise
        return side

    def sidecar(self, key):
        """The Sidecar for `key`, or None when the store has none for it, or one this module cannot read."""
        try:
            with open(self.sidecar_path(key), encoding="utf-8") as f:
                d = json.load(f)
            return Sidecar(**{k: d[k] for k in FIELDS})
        except (OSError, ValueError, KeyError, TypeError):
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
