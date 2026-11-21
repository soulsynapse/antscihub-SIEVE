"""The candidate store of docs/playground/contract.md: a memory tier over a disk tier, under budgets.

It reaches a disk only through the object it is handed (`write`, `rename`, `read`, `names`,
`delete`, `size`, `touched`, `used`, `write_seconds`, `read_seconds`), so the simulation hands it a simulated one and the player a real one.
"""
import heapq
from dataclasses import dataclass

ENTRIES, MANIFESTS, PARTS = "entries/", "checkpoints/", "parts/"


class Refused(Exception):
    """A budget cannot hold what was asked; the message carries the need and the budget."""


@dataclass(frozen=True)
class Address:
    key: str
    chunk: int

    @property
    def name(self):
        return f"{ENTRIES}{self.key}/{self.chunk}"


def address_of(name):
    key, chunk = name[len(ENTRIES):].rsplit("/", 1)
    return Address(key, int(chunk))


class Store:
    """One store over `disk`. `writer` names this opener among others on the same disk, so no two
    write one temporary name. `emit(kind, address, tier)` is told each hit, miss, put, letting go
    and refusal. `atomic=False` writes an entry in place, which the contract forbids and the
    simulation uses to show its oracle sees a torn entry. `worth=True` ranks what is held by
    the seconds a byte it saves (GreedyDual-Size) and keeps off the disk what is quicker to make
    again than to write; False ranks by recency and writes everything."""

    def __init__(self, disk, memory, disk_budget, writer="a", emit=None, atomic=True, worth=True):
        self.disk, self.memory, self.disk_budget = disk, memory, disk_budget
        self.writer, self.emit, self.atomic = writer, emit or (lambda *a: None), atomic
        self.worth = worth
        self.held, self.rank, self.heap = {}, {}, []
        self.low, self.ticks = 0.0, 0
        self.held_bytes = 0
        self.reserved = 0
        self.parts = 0

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

    def put(self, address, value, size, cost=0.0, keep=False, hold=True):
        """Keep `value`, which took `cost` seconds to make, under `address`. It goes to disk when
        `keep` says so or the policy finds it worth the write, and the disk budget has room; and
        to memory when `hold` and the memory budget allow."""
        wanted = keep or not self.worth or cost >= self.disk.write_seconds(size)
        if wanted and self.disk.size(address.name) is None:
            if self._make_room(size):
                self._land(address.name, value, size)
                self.emit("put", address, "disk")
            else:
                self.emit("refused", address, "disk")
        if hold:
            self._hold(address, value, size, cost)

    def to_disk(self, address):
        """Write an entry held in memory to disk whatever the policy thinks of it; whether it is there."""
        if self.disk.size(address.name) is None and address in self.held and self._make_room(self.held[address][1]):
            self._land(address.name, *self.held[address][:2])
        return self.disk.size(address.name) is not None

    def forget(self):
        """Hold nothing in memory, as after the folder changed underneath."""
        self.held, self.rank, self.heap, self.held_bytes = {}, {}, [], 0

    def reserve(self, size):
        """Take `size` bytes of the memory budget for work under way, letting go of what is held
        to make them free, until `release(size)`. Reservations add; what is held and what is
        reserved together never pass the budget."""
        if self.reserved + size > self.memory:
            raise Refused(f"work needing {self.reserved + size} bytes at once under a memory budget of {self.memory}")
        self.reserved += size
        self._shrink(0)

    def release(self, size):
        self.reserved -= size

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

    def covered(self, key, chunks):
        """Which of `chunks` of `key` an ask would be answered for without computing."""
        return [c for c in chunks if Address(key, c) in self.held
                or self.disk.size(Address(key, c).name) is not None]

    def drop(self, address, tier=None):
        if tier in (None, "memory") and address in self.held:
            self.held_bytes -= self.held.pop(address)[1]
            del self.rank[address]
        if tier in (None, "disk") and address not in self.named():
            self.disk.delete(address.name)

    def checkpoint(self, name, snapshot, addresses):
        """Name `addresses` and `snapshot` as a checkpoint. Refused, naming nothing, when an
        address is not on disk or the manifests together would pass the disk budget."""
        absent = [a for a in addresses if self.disk.size(a.name) is None]
        if absent:
            raise Refused(f"checkpoint {name}: {len(absent)} of {len(addresses)} entries are not on disk")
        named = self.named() | set(addresses)
        need = sum(self.disk.size(a.name) or 0 for a in named)
        if need > self.disk_budget:
            raise Refused(f"checkpoint {name}: the checkpoints would hold {need} bytes of a disk budget of {self.disk_budget}")
        self._land(MANIFESTS + name, (snapshot, tuple(addresses)), 0)

    def manifest(self, name):
        found = self.disk.read(MANIFESTS + name)
        return None if found is None else found[0]

    def named(self):
        """Every address a manifest on the disk names."""
        out = set()
        for name in self.disk.names(MANIFESTS):
            found = self.disk.read(name)
            if found is not None:
                out |= set(found[0][1])
        return out

    def gone(self):
        """The addresses a manifest names that the disk does not hold whole."""
        return {a for a in self.named() if self.disk.size(a.name) is None}

    def _land(self, name, value, size):
        if not self.atomic:
            self.disk.write(name, value, size)
            return
        self.parts += 1
        part = f"{PARTS}{self.writer}-{self.parts}"
        self.disk.write(part, value, size)
        self.disk.rename(part, name)

    def _make_room(self, size):
        """Whether `size` more bytes fit the disk budget, after letting go of the entries no
        manifest names that were touched longest ago, down to nine tenths of the budget."""
        if size > self.disk_budget:
            return False
        used = self.disk.used()
        if used + size <= self.disk_budget:
            return True
        named = self.named()
        for name in sorted(self.disk.names(ENTRIES), key=self.disk.touched):
            if address_of(name) in named:
                continue
            used -= self.disk.size(name)
            self.disk.delete(name)
            self.emit("let go", address_of(name), "disk")
            if used + size <= self.disk_budget * 0.9:
                break
        return used + size <= self.disk_budget

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
