"""The candidate store of docs/playground/contract.md: a memory tier over a disk tier, under budgets.

It reaches a disk only through the object it is handed (`write`, `rename`, `read`, `names`,
`delete`, `size`, `age`, `touch`, `used`, `budgeted`, `write_seconds`, `read_seconds`, `mark`, `marked`, `lock`), so the
simulation hands it a simulated one and the player a real one.
"""
import heapq
from contextlib import nullcontext
from dataclasses import dataclass

SURE = 10      # a value costing this many times its write to make goes to disk the first time it is made
GRACE = 2000   # the age, in the disk's own measure, past which a part or a pending manifest is a crash's leaving
ENTRIES, MANIFESTS, PARTS = "entries/", "checkpoints/", "parts/"
PENDING = ".pending"   # a manifest whose entries are still being filled; it names them, and is no checkpoint yet


class Refused(Exception):
    """A budget cannot hold what was asked; the message carries the need and the budget."""


@dataclass(frozen=True, order=True)
class Address:
    key: str
    chunk: int

    @property
    def name(self):
        return f"{ENTRIES}{self.key}/{self.chunk}"


def address_of(name):
    """The address a file under `ENTRIES` is the entry of, None of a file that is no entry's."""
    key, _, chunk = name[len(ENTRIES):].rpartition("/")
    return Address(key, int(chunk)) if key and chunk.isdecimal() else None


class Store:
    """One store over `disk`. `writer` names this opener among others on the same disk, so no two
    write one temporary name. `emit(kind, what, tier)` is told each hit, miss, put, letting go and
    refusal. `worth=True` ranks what memory holds by the seconds a byte it saves (GreedyDual-Size)
    and writes to disk at once only what cost `SURE` times its write to make, and what cost at
    least its write the second time it is made; False ranks by recency and writes everything.
    `atomic=False` writes an entry in place and `locked=False` lets go and names without the
    disk's lock; the contract forbids both and the simulation uses them to show its oracles see."""

    def __init__(self, disk, memory, disk_budget, writer="a", emit=None, atomic=True, worth=True, locked=True):
        self.disk, self.memory, self.disk_budget = disk, memory, disk_budget
        self.writer, self.emit = writer, emit or (lambda *a: None)
        self.atomic, self.worth, self.locked = atomic, worth, locked
        self.held, self.rank, self.heap = {}, {}, []
        self.low, self.ticks = 0.0, 0
        self.held_bytes = 0
        self.reserved = 0
        self.parts = 0
        disk.budgeted(disk_budget)

    def get(self, address):
        if address in self.held:
            self._rank(address)
            self.emit("hit", address, "memory")
            return self.held[address][0]
        found = self.disk.read(address.name)
        if found is None:
            self.emit("miss", address, None)
            return None
        value, size = found
        self.emit("hit", address, "disk")
        self._hold(address, value, size, self.disk.read_seconds(size))
        return value

    def put(self, address, value, size, cost=0.0, keep=False, spare=False, memory_only=False):
        """Keep `value`, which took `cost` seconds to make, under `address`. It goes to disk when
        `keep` says so or the policy finds it worth the write, and the disk budget has room,
        never when `memory_only`; and to memory when the budget allows, which under `spare` is
        only when nothing held has to be let go for it."""
        wanted = not memory_only and (keep or not self.worth)
        if self.worth and not memory_only and not wanted:
            write, again = self.disk.write_seconds(size), self.disk.marked(address.name)
            room = self.disk.used() + size <= self.disk_budget * 0.9   # nothing is let go for a maybe
            wanted = cost >= SURE * write or (again and cost >= write and room)
            self.disk.mark(address.name)
        if wanted and self.disk.size(address.name) is None:
            if self._make_room(size) and self._land(address.name, value, size, durable=keep):
                self.emit("put", address, "disk")
            else:
                self.emit("refused", address, "disk")
        if not (spare and self.held_bytes + self.reserved + size > self.memory):
            self._hold(address, value, size, cost)

    def to_disk(self, address):
        """Write an entry held in memory to disk whatever the policy thinks of it; whether it is there."""
        if self.disk.size(address.name) is None and address in self.held and self._make_room(self.held[address][1]):
            self._land(address.name, *self.held[address][:2], durable=True)
        return self.disk.size(address.name) is not None

    def forget(self):
        """Hold nothing in memory, as after the folder changed underneath."""
        self.held, self.rank, self.heap, self.held_bytes = {}, {}, [], 0

    def reserve(self, size):
        """Take `size` bytes of the memory budget for work under way, letting go of what is held
        to make them free, until `release(size)`. Reservations add; what is held and what is
        reserved together never pass the budget."""
        if self.reserved + size > self.memory:
            self.emit("refused", size, "memory")
            raise Refused(f"work needing {self.reserved + size} bytes at once under a memory budget of {self.memory}")
        self.reserved += size
        self._shrink(0)

    def release(self, size):
        self.reserved -= size

    def covered(self, key, chunks):
        """Which of `chunks` of `key` an ask would be answered for without computing."""
        return [c for c in chunks if Address(key, c) in self.held
                or self.disk.size(Address(key, c).name) is not None]

    def drop(self, address, tier=None):
        """Let go of an entry, in one tier or both; on disk never one a manifest names."""
        if tier in (None, "memory") and address in self.held:
            self.held_bytes -= self.held.pop(address)[1]
            del self.rank[address]
            self.emit("let go", address, "memory")
        if tier in (None, "disk"):
            try:
                with self._lock():
                    if address not in self.named() and self.disk.size(address.name) is not None:
                        self.disk.delete(address.name)
                        self.emit("let go", address, "disk")
            except OSError:
                pass

    def checkpoint(self, name, snapshot, addresses, sizes, fill):
        """Name `addresses`, of `sizes` bytes, and `snapshot` as a checkpoint, calling
        `fill(address)` for each not on disk. Refused before any filling, with the figures, when
        it and the checkpoints kept would pass the disk budget; refused after, naming nothing,
        when an entry is still not on disk, when the manifest will not land, or when `name` is a
        checkpoint already. A pending manifest lands before the filling, so filling one entry lets
        go of no other; the finished one lands after a look under the lock, beside it and never
        over a checkpoint that stands."""
        kept = sum(self.disk.size(a.name) or 0 for a in self.named() - set(addresses))
        if kept + sum(sizes) > self.disk_budget:
            self.emit("refused", name, "disk")
            raise Refused(f"checkpoint {name}: its {sum(sizes)} bytes and the {kept} of the checkpoints kept "
                          f"pass a disk budget of {self.disk_budget}")
        at, body = MANIFESTS + name, (snapshot, tuple(addresses))
        try:
            if self.disk.size(at) is not None:
                raise Refused(f"checkpoint {name}: there is one of that name; let it go first")
            if not self._land(at + PENDING, body, 0, durable=True):
                raise Refused(f"checkpoint {name}: its manifest could not be written")
            for address in addresses:
                if self.disk.size(address.name) is None:
                    fill(address)
                    self.disk.touch(at + PENDING)
            try:
                with self._lock():
                    absent = [a for a in addresses if self.disk.size(a.name) is None]
            except OSError as error:
                raise Refused(f"checkpoint {name}: the folder's lock could not be taken") from error
            if absent:
                raise Refused(f"checkpoint {name}: {len(absent)} of {len(addresses)} entries are not on disk")
            if not self._land(at, body, 0, durable=True) or self.disk.read(at, touch=False) is None:
                raise Refused(f"checkpoint {name}: its manifest could not be written")
        except Refused:
            self.emit("refused", name, "disk")
            raise
        finally:
            self.disk.delete(at + PENDING)

    def release_checkpoint(self, name):
        """Name nothing by `name` any longer, its entries then let go as any others are; whether
        it is gone, which it is not while another process holds its manifest open."""
        self.disk.delete(MANIFESTS + name)
        return self.disk.size(MANIFESTS + name) is None

    def manifest(self, name):
        """(snapshot, addresses) of a finished checkpoint, None of one unfinished or absent."""
        found = self.disk.read(MANIFESTS + name, touch=False)
        return found[0] if found is not None else None

    def named(self):
        """Every address a manifest on the disk names, a pending one's among them."""
        out = set()
        for name in self.disk.names(MANIFESTS):
            found = self.disk.read(name, touch=False)
            if found is not None:
                out |= set(found[0][1])
        return out

    def gone(self):
        """Checkpoint name -> the addresses it names that the disk does not hold, for each
        finished checkpoint missing any."""
        out = {}
        for name in self.disk.names(MANIFESTS):
            found = None if name.endswith(PENDING) else self.disk.read(name, touch=False)
            if found is not None:
                missing = [a for a in found[0][1] if self.disk.size(a.name) is None]
                if missing:
                    out[name[len(MANIFESTS):]] = missing
        return out

    def _lock(self):
        return self.disk.lock() if self.locked else nullcontext()

    def _land(self, name, value, size, durable=False):
        """Whether `value` is now under `name`, whole; a disk that refuses the write is no error."""
        if not self.atomic:
            return self.disk.write(name, value, size, durable)
        self.parts += 1
        part = f"{PARTS}{self.writer}-{self.parts}"
        return self.disk.write(part, value, size, durable) and self.disk.rename(part, name)

    def _make_room(self, size):
        """Whether `size` more bytes fit the disk budget, after letting go under the lock of what
        a crash left and then of entries no manifest names, those touched longest ago first, down
        to nine tenths of the budget."""
        if size > self.disk_budget:
            return False
        if self.disk.used() + size <= self.disk_budget:
            return True
        try:
            with self._lock():
                for name in self.disk.names(PARTS) + [n for n in self.disk.names(MANIFESTS) if n.endswith(PENDING)]:
                    age = self.disk.age(name)
                    if age is not None and age > GRACE:
                        self.disk.delete(name)
                named = self.named()
                loose = sorted(((age, n) for n in self.disk.names(ENTRIES)
                                if (age := self.disk.age(n)) is not None
                                and (a := address_of(n)) is not None and a not in named), reverse=True)
                used = self.disk.used()
                for _, name in loose:
                    if used + size <= self.disk_budget * 0.9:
                        break
                    used -= self.disk.size(name) or 0
                    self.disk.delete(name)
                    self.emit("let go", address_of(name), "disk")
        except OSError:
            return False
        return self.disk.used() + size <= self.disk_budget

    def _shrink(self, size):
        while self.held and self.held_bytes + size > self.memory - self.reserved:
            rank, _, old = heapq.heappop(self.heap)
            if self.rank.get(old) != rank:
                continue
            if self.worth:
                self.low = rank
            self.held_bytes -= self.held.pop(old)[1]
            del self.rank[old]
            self.emit("let go", old, "memory")

    def _rank(self, address):
        _, size, cost = self.held[address]
        self.ticks += 1
        self.rank[address] = self.low + cost / max(size, 1) if self.worth else self.ticks
        heapq.heappush(self.heap, (self.rank[address], self.ticks, address))

    def _hold(self, address, value, size, cost=0.0):
        if address in self.held:
            self._rank(address)
            return
        if size > self.memory - self.reserved:
            self.emit("refused", address, "memory")
            return
        self._shrink(size)
        self.held[address] = (value, size, cost)
        self.held_bytes += size
        self._rank(address)
