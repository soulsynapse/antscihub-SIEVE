"""A real folder as store.py's disk: the same calls the simulated Disk answers, over files.

An entry's file is a header of a magic, the payload's length and its crc32, then the pickled
value; a file whose header, length or checksum is wrong is no entry. Ages are seconds by the
file's own modified time against this machine's clock. No call raises for what another process
or the filesystem did to a file: a refusal is an answer of None or False.
"""
import os
import pickle
import struct
import time
import zlib
from contextlib import contextmanager

MAGIC = b"SIEV1"
HEAD = struct.Struct("<5sQI")
TOUCH = 60.0        # a read moves an entry's time only when it is older than this, so reads seldom write
RECOUNT = 30.0      # how long a count of the folder's bytes is trusted before it is walked again
STALE_LOCK = 120.0  # a lock watched unchanged for this long was left by a crash and is taken over
RENAMES = 40        # tries at a rename another process's open handle refuses, 5 ms apart


class Folder:
    """`root` as a disk of several writers. `file_s` and the two rates price a write and a read
    for the store's policy; diskrate.py measures them. `now`, `tick` and `wait` are handed in by
    a test."""

    def __init__(self, root, writer="a", file_s=0.0015, write_bps=1.6e9, read_bps=2e9,
                 now=time.time, tick=time.monotonic, wait=time.sleep):
        self.root, self.writer, self.now, self.tick, self.wait = root, writer, now, tick, wait
        self.file_s, self.write_bps, self.read_bps = file_s, write_bps, read_bps
        self.recount_after = None
        os.makedirs(root, exist_ok=True)
        self._used, self._counted, self._written, self._depth, self._mine = 0, None, 0, 0, None
        self._made = set()
        for name in os.listdir(root):
            if name.startswith("made-"):
                try:
                    with open(os.path.join(root, name), encoding="utf-8") as f:
                        self._made.update(line.strip() for line in f)
                except (OSError, UnicodeError):
                    pass

    def _path(self, name):
        return os.path.join(self.root, *name.split("/"))

    def write(self, name, value, size, durable=False):
        """Whether `value` is written whole under `name`. `durable` flushes it to the disk first,
        which is the cost of a small write; without it a power loss may leave a file its checksum
        refuses. `size` is the store's reckoning and unused, the file's own bytes being counted."""
        payload = pickle.dumps(value, protocol=5)
        path = self._path(name)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(HEAD.pack(MAGIC, len(payload), zlib.crc32(payload)))
                f.write(payload)
                if durable:
                    f.flush()
                    os.fsync(f.fileno())
        except OSError:
            self.delete(name)
            return False
        self._used += HEAD.size + len(payload)
        self._written += HEAD.size + len(payload)
        return True

    def rename(self, old, new):
        """Whether `new` now holds a whole file: `old`, or an entry already there, two values
        under one entry's name being equal. `old` is let go when it could not be moved."""
        src, dst = self._path(old), self._path(new)
        entry = new.startswith("entries/")
        for _ in range(RENAMES):
            if entry and self.size(new) is not None:
                break
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.replace(src, dst)
                return True
            except FileNotFoundError:
                break
            except OSError:
                self.wait(0.005)
        self.delete(old)
        return self.size(new) is not None

    def read(self, name, touch=True):
        path = self._path(name)
        try:
            with open(path, "rb") as f:
                head = f.read(HEAD.size)
                if len(head) < HEAD.size:
                    return None
                magic, length, crc = HEAD.unpack(head)
                payload = f.read(length + 1)
            if magic != MAGIC or len(payload) != length or zlib.crc32(payload) != crc:
                return None
            value = pickle.loads(payload)
        except Exception:
            return None
        if touch:
            try:
                if self.now() - os.path.getmtime(path) > TOUCH:
                    os.utime(path, (self.now(), self.now()))
            except OSError:
                pass
        return value, HEAD.size + length

    def budgeted(self, size):
        """The store's budget of bytes here. The count is walked again once this writer has written
        a twentieth of it, which bounds how far several writers pass it between them."""
        self.recount_after = size // 20

    def touch(self, name):
        try:
            os.utime(self._path(name), (self.now(), self.now()))
        except OSError:
            pass

    def names(self, prefix):
        top = self._path(prefix.rstrip("/"))
        return [os.path.relpath(os.path.join(at, f), self.root).replace(os.sep, "/")
                for at, _, files in os.walk(top) for f in files]

    def delete(self, name):
        try:
            size = os.path.getsize(self._path(name))
            os.remove(self._path(name))
            self._used -= size
        except OSError:
            pass

    def size(self, name):
        """The bytes of a file that is as long as its header says, None of any other: a file cut
        short is not there. The checksum is a read's to try."""
        try:
            with open(self._path(name), "rb") as f:
                magic, length, _ = HEAD.unpack(f.read(HEAD.size))
                whole = magic == MAGIC and os.fstat(f.fileno()).st_size == HEAD.size + length
            return HEAD.size + length if whole else None
        except (OSError, struct.error):
            return None

    def age(self, name):
        try:
            return self.now() - os.path.getmtime(self._path(name))
        except OSError:
            return None

    def used(self):
        """The folder's bytes: walked when the last walk is old or this writer has written much
        since, and this writer's own writes and deletes after. Other writers' doings since the
        walk are not in it."""
        much = self.recount_after is not None and self._written >= self.recount_after
        if self._counted is None or much or self.now() - self._counted > RECOUNT:
            total = 0
            for at, _, files in os.walk(self.root):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(at, f))
                    except OSError:
                        pass
            self._used, self._counted, self._written = total, self.now(), 0
        return self._used

    def write_seconds(self, size):
        return self.file_s + size / self.write_bps

    def read_seconds(self, size):
        return self.file_s + size / self.read_bps

    def mark(self, name):
        if name not in self._made:
            self._made.add(name)
            try:
                with open(os.path.join(self.root, f"made-{self.writer}.log"), "a", encoding="utf-8", newline="\n") as f:
                    f.write(name + "\n")
            except OSError:
                pass

    def marked(self, name):
        return name in self._made

    @contextmanager
    def lock(self):
        """The folder's one lock: a folder made and removed, which a filesystem does whole. A lock
        is taken over when this process has watched the same one for `STALE_LOCK` by its own
        clock, no two machines' clocks being compared; one that will not be made a quarter as
        long again after that raises OSError. The count is walked afresh inside it, so letting go reckons with what
        other writers wrote."""
        at = os.path.join(self.root, "lock")
        if self._depth == 0:
            began = since = self.tick()
            seen = None
            while True:
                try:
                    os.mkdir(at)
                    break
                except OSError:
                    pass
                stamp = self._stamp(at)
                if stamp != seen:
                    seen, since = stamp, self.tick()
                elif stamp is not None and self.tick() - since > STALE_LOCK:
                    try:
                        os.rmdir(at)
                    except OSError:
                        pass
                    seen = None
                if self.tick() - began > 1.25 * STALE_LOCK:
                    raise OSError(f"the lock of {self.root} could not be taken")
                self.wait(0.005)
            self._mine = self._stamp(at)
            self._counted = None
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1
            if self._depth == 0 and self._stamp(at) == self._mine:
                try:
                    os.rmdir(at)
                except OSError:
                    pass

    @staticmethod
    def _stamp(path):
        try:
            return os.stat(path).st_mtime_ns
        except OSError:
            return None
