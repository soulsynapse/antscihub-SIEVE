"""A real folder as store.py's disk: the same calls the simulated Disk answers, over files.

An entry's file is a header of a magic, the payload's length and its crc32, then the pickled
value; a file whose header, length or checksum is wrong is no entry. Ages are seconds by the
file's own modified time against this machine's clock.
"""
import os
import pickle
import struct
import time
import zlib
from contextlib import contextmanager

MAGIC = b"SIEV1"
HEAD = struct.Struct("<5sQI")
TOUCH = 60.0       # a read moves a file's time only when it is older than this, so reads seldom write
RECOUNT = 30.0     # how long a count of the folder's bytes is trusted before it is walked again
STALE_LOCK = 30.0  # a lock older than this was left by a crash and is taken over
PASSED_OVER = (PermissionError, FileNotFoundError)   # Windows refuses a file another process holds open


class Folder:
    """`root` as a disk of several writers. `file_s` and the two rates price a write and a read
    for the store's policy; diskrate.py measures them. `now` and `wait` are handed in by a test."""

    def __init__(self, root, writer="a", file_s=0.0015, write_bps=1.6e9, read_bps=2e9, now=time.time, wait=time.sleep):
        self.root, self.writer, self.now, self.wait = root, writer, now, wait
        self.file_s, self.write_bps, self.read_bps = file_s, write_bps, read_bps
        os.makedirs(root, exist_ok=True)
        self._used, self._counted, self._depth = 0, None, 0
        self._made = set()
        for name in os.listdir(root):
            if name.startswith("made-"):
                with open(os.path.join(root, name), encoding="utf-8") as f:
                    self._made.update(line.strip() for line in f)

    def _path(self, name):
        return os.path.join(self.root, *name.split("/"))

    def write(self, name, value, size):
        """Write `value` whole and flushed under `name`; `size` is the store's reckoning and unused,
        the file's own bytes being what this disk counts."""
        payload = pickle.dumps(value, protocol=5)
        path = self._path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(HEAD.pack(MAGIC, len(payload), zlib.crc32(payload)))
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        self._used += HEAD.size + len(payload)

    def rename(self, old, new):
        """Land `old` as `new`. A `new` already there is kept and `old` let go, two values under
        one name being equal; so is `old` when Windows will not move it."""
        src, dst = self._path(old), self._path(new)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            if new.startswith("entries/") and self.size(new) is not None:
                raise PermissionError
            os.replace(src, dst)
        except PASSED_OVER:
            self.delete(old)

    def read(self, name):
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
            if self.now() - os.path.getmtime(path) > TOUCH:
                os.utime(path, (self.now(), self.now()))
        except (OSError, struct.error):
            return None
        return pickle.loads(payload), HEAD.size + length

    def names(self, prefix):
        top = self._path(prefix.rstrip("/"))
        return [os.path.relpath(os.path.join(at, f), self.root).replace(os.sep, "/")
                for at, _, files in os.walk(top) for f in files]

    def delete(self, name):
        try:
            size = os.path.getsize(self._path(name))
            os.remove(self._path(name))
            self._used -= size
        except PASSED_OVER:
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
        """The folder's bytes: walked when the last walk is old, and this writer's own writes and
        deletes since. Other writers' doings since the walk are not in it."""
        if self._counted is None or self.now() - self._counted > RECOUNT:
            self._used = sum(os.path.getsize(os.path.join(at, f)) for at, _, files in os.walk(self.root) for f in files
                             if os.path.exists(os.path.join(at, f)))
            self._counted = self.now()
        return self._used

    def write_seconds(self, size):
        return self.file_s + size / self.write_bps

    def read_seconds(self, size):
        return self.file_s + size / self.read_bps

    def mark(self, name):
        if name not in self._made:
            self._made.add(name)
            with open(os.path.join(self.root, f"made-{self.writer}.log"), "a", encoding="utf-8", newline="\n") as f:
                f.write(name + "\n")

    def marked(self, name):
        return name in self._made

    @contextmanager
    def lock(self):
        """The folder's one lock: a folder made and removed, which a filesystem does whole. The
        count is walked afresh inside it, so letting go reckons with what other writers wrote."""
        at = os.path.join(self.root, "lock")
        if self._depth == 0:
            while True:
                try:
                    os.mkdir(at)
                    break
                except FileExistsError:
                    try:
                        if self.now() - os.path.getmtime(at) > STALE_LOCK:
                            os.rmdir(at)
                            continue
                    except OSError:
                        continue
                    self.wait(0.005)
            self._counted = None
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1
            if self._depth == 0:
                try:
                    os.rmdir(at)
                except OSError:
                    pass
