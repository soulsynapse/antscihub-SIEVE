"""A simulated machine, pipeline and user for docs/playground/sim/store.py, and the oracles over them.

Time, disk and memory are simulated, so an hour's walk costs milliseconds and a seed replays a run.
What a tool would compute is a digest of everything it truly depends on (`World.truth`); what the
store is asked under is a key made by a scheme (`World.key`), so a scheme that leaves something out
of the key serves a wrong value and O1 sees it. Run: python docs/playground/sim/sim.py [seeds].
"""
import hashlib
import random
import statistics
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path

sys.path[:0] = [str(Path(__file__).parent), str(Path(__file__).parents[3])]
from sieve_player.result_store import Address, Refused, Store, address_of  # noqa: E402

MB, GB = 1 << 20, 1 << 30
sys.setrecursionlimit(100000)
WITHIN = 3.5      # the most threads or processes inside one clip gain, by figures.md
AHEAD = 40        # rows a decoder reads forward to reach a row sooner than it seeks
PLANE = 64 << 10  # a result of more bytes a row than this is a plane and not a table
TORN = "torn"


def digest(*parts):
    return hashlib.sha1(repr(parts).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class Profile:
    name: str
    cores: int
    memory: int
    disk: int
    read_bps: float
    write_bps: float
    seek_s: float
    file_s: float   # what a file costs to make and rename whatever its size
    slow: float = 1.0   # how many times slower a core is than on figures.md's machine


PROFILES = {   # the desktop is figures.md's machine, its writes by diskrate.py; reads and the other two are guesses
    "laptop": Profile("laptop", 4, 3 * GB, 40 * GB, 150 * MB, 120 * MB, 0.008, 0.003, 2.5),
    "desktop": Profile("desktop", 32, 24 * GB, 500 * GB, 2000 * MB, 1600 * MB, 0.0002, 0.0015),
    "usb-hdd": Profile("usb-hdd", 32, 24 * GB, 500 * GB, 200 * MB, 235 * MB, 0.012, 0.0032),
    "hpc": Profile("hpc", 64, 200 * GB, 5000 * GB, 300 * MB, 300 * MB, 0.005, 0.005, 1.3),
}


@dataclass(frozen=True)
class Scheme:
    """What is being tried: what a key holds, how an entry lands, how many rows a chunk is."""
    code_in_key: bool = True
    strong_print: bool = True
    atomic: bool = True
    chunk_bytes: int = 64 * MB   # a chunk is as many rows as fit this, by the pipeline's widest row
    worth: bool = True           # the store's policy, see Store
    locked: bool = True
    window_apart: bool = True    # a window's value is addressed with its range, apart from an exact one


class Crash(Exception):
    pass


class Disk:
    """A folder as several stores see it, charging the clock for each read and write. A write is
    two steps, begun and whole; `crash_in` counts steps to a crash, which leaves a begun file torn."""

    def __init__(self, profile, clock):
        self.profile, self.clock, self.files, self.crash_in, self.ticks = profile, clock, {}, None, 0
        self.total, self.made, self.low, self.meddle, self.busy = 0, set(), 0.0, None, False

    def _step(self):
        if self.crash_in is not None:
            self.crash_in -= 1
            if self.crash_in < 0:
                self.crash_in = None
                raise Crash()

    def write(self, name, value, size, durable=False, worth=0.0):
        self.total += size - (self.size(name) or 0)
        self.files[name] = [TORN, size, self._tick(), self.low + worth, worth]
        self._step()
        self.clock[0] += self.write_seconds(size)
        self.files[name][0] = value
        self._step()
        return True

    def rename(self, old, new):
        self.total -= self.files[new][1] if new in self.files else 0
        self.files[new] = self.files.pop(old)
        return True

    def budgeted(self, size):
        pass

    def touch(self, name):
        if name in self.files:
            self.files[name][2] = self._tick()

    @contextmanager
    def lock(self):
        """No other writer takes a turn while this is held."""
        was, self.busy = self.busy, True
        try:
            yield
        finally:
            self.busy = was

    def read(self, name, touch=True):
        if name not in self.files:
            return None
        self._meddled()
        if name not in self.files:
            return None
        value, size = self.files[name][:2]
        if touch:
            self.files[name][2:4] = self._tick(), self.low + self.files[name][4]
        self.clock[0] += self.profile.seek_s + size / self.profile.read_bps
        return value, size

    def size(self, name):
        self._meddled()
        return self.files[name][1] if name in self.files else None

    def _meddled(self):
        """Let another writer on the folder take a turn, between any two steps of this one."""
        if self.meddle is not None and not self.busy:
            turn, self.meddle = self.meddle, None
            try:
                turn()
            finally:
                self.meddle = turn

    def names(self, prefix):
        return [n for n in self.files if n.startswith(prefix)]

    def delete(self, name):
        self.total -= self.files.pop(name, (0, 0))[1]

    def mark(self, name):
        self.made.add(name)

    def marked(self, name):
        return name in self.made

    def age(self, name):
        return self.ticks - self.files[name][2] if name in self.files else None

    def rank(self, name):
        return self.files[name][3] if name in self.files else None

    def floor(self):
        return self.low

    def lift(self, floor):
        self.low = max(self.low, floor)

    def write_seconds(self, size):
        return self.profile.file_s + size / self.profile.write_bps

    def read_seconds(self, size):
        return self.profile.seek_s + size / self.profile.read_bps

    def used(self):
        return self.total

    def _tick(self):
        self.ticks += 1
        return self.ticks


@dataclass
class Tool:
    name: str
    kind: str            # "frame": a chunk of its inputs' same chunk; "stepped": and of its own chunk before; "whole": one chunk of all of its input's; "reach": of its input's rows within its node's `reach` either side
    ms_per_row: float
    bytes_per_row: int
    code: int = 0


@dataclass
class Node:
    name: str
    tool: str
    reads: tuple = ()
    params: dict = field(default_factory=dict)
    computed: frozenset = frozenset()   # the params its run reads; the rest are a draw's
    cut_by: str = None                  # a gate whose result says which chunks this node has


def pipeline(footage="1080p"):
    """The tools, the nodes and the seconds a decoder's seek takes, for a document like the ants
    one. Priced from figures.md at 1080p; at 5.3K by that file where it has a figure and by the
    count of pixels where it has none."""
    big = footage == "5.3K"
    px = 7.6 if big else 1.0
    tools = {t.name: t for t in (
        Tool("decode", "frame", 31.0 if big else 2.0, int(6.2 * MB * px)),
        Tool("gray", "frame", 1.5 if big else 0.2, int(2 * MB * px)),
        Tool("motion", "frame", 0.5 * px, int(2 * MB * px)), Tool("energy", "frame", 0.12 * px, 64),
        Tool("gate", "whole", 0.002, 16), Tool("detect", "frame", 2.4 * px, 1200),
        Tool("track", "stepped", 0.75, 1208), Tool("smooth", "reach", 0.001, 8),
        Tool("trail", "stepped", 0.01, 64))}
    nodes = {n.name: n for n in (
        Node("video", "decode"), Node("gray", "gray", ("video",)),
        Node("motion", "motion", ("gray",), {"span": 2}, frozenset({"span"})),
        Node("energy", "energy", ("motion",)),
        Node("gate", "gate", ("energy",), {"keep": 20}, frozenset({"keep"})),
        Node("detect", "detect", ("gray",), {"level": 40, "outline": 1}, frozenset({"level"}), "gate"),
        Node("track", "track", ("detect",), {"reach": 8}, frozenset({"reach"}), "gate"),
        Node("smooth", "smooth", ("energy",), {"reach": 5}, frozenset({"reach"})),
        Node("trail", "trail", ("energy",)))}
    return tools, nodes, (0.49 if big else 0.1)


class World:
    """The document, the tools' code and the footage as they are now."""

    def __init__(self, rows, scheme, footage="1080p"):
        self.tools, self.nodes, self.seek_s = pipeline(footage)
        self.rows, self.scheme = rows, scheme
        self.footage = ["content-0", "size-0"]   # what the file holds; what its size and ends say
        self.chunk = max(1, scheme.chunk_bytes // max(t.bytes_per_row for t in self.tools.values()))
        self.chunks = -(-rows // self.chunk)
        self._memo = {}

    def changed(self):
        self._memo.clear()

    def made(self):
        """What no snapshot brings back: the tools' code and the footage."""
        return tuple(t.code for t in self.tools.values()), self.footage[0]

    def snapshot(self):
        return {n.name: dict(n.params) for n in self.nodes.values()}, self.made()

    def restore(self, snapshot):
        for name, params in snapshot[0].items():
            self.nodes[name].params = dict(params)
        self.changed()

    def chunks_of(self, name):
        """The chunks a node has: one for a whole tool, those its gate keeps for a cut node."""
        node = self.nodes[name]
        if self.tools[node.tool].kind == "whole":
            return [0]
        if node.cut_by is None:
            return list(range(self.chunks))
        if ("chunks", name) not in self._memo:
            gate, keep = self.truth(node.cut_by, 0), self.nodes[node.cut_by].params["keep"]
            self._memo["chunks", name] = [c for c in range(self.chunks) if int(digest(gate, c), 16) % 100 < keep]
        return self._memo["chunks", name]

    def before(self, name, chunk):
        """The chunk of a node next before `chunk`, or None at its first."""
        if ("before", name) not in self._memo:
            kept = self.chunks_of(name)
            self._memo["before", name] = dict(zip(kept[1:], kept))
        return self._memo["before", name].get(chunk)

    def reads_of(self, name, chunk):
        """The (node, chunk) pairs computing this chunk reads, its own chunk before among them."""
        node, out = self.nodes[name], []
        kind = self.tools[node.tool].kind
        for read in node.reads:
            if self.tools[self.nodes[read].tool].kind == "whole":
                out.append((read, 0))
            elif kind == "whole":
                out += [(read, c) for c in self.chunks_of(read)]
            elif kind == "reach":
                span = -(-node.params["reach"] // self.chunk)
                out += [(read, c) for c in range(chunk - span, chunk + span + 1) if 0 <= c < self.chunks]
            else:
                out.append((read, chunk))
        if node.cut_by:
            out.append((node.cut_by, 0))
        if kind == "stepped":
            if self.before(name, chunk) is not None:
                out.append((name, self.before(name, chunk)))
        return out

    def truth(self, name, chunk):
        at = ("truth", name, chunk)
        if at not in self._memo:
            node = self.nodes[name]
            tool = self.tools[node.tool]
            read = tuple(self.truth(n, c) for n, c in self.reads_of(name, chunk))
            params = tuple(sorted((k, v) for k, v in node.params.items() if k in node.computed))
            self._memo[at] = digest(tool.name, tool.code, params, read, chunk * self.chunk, self.chunk,
                                    None if node.reads else self.footage[0])
        return self._memo[at]

    def key(self, name):
        at = ("key", name)
        if at not in self._memo:
            node, s = self.nodes[name], self.scheme
            tool = self.tools[node.tool]
            params = tuple(sorted((k, v) for k, v in node.params.items() if k in node.computed))
            footage = None if node.reads else self.footage[0 if s.strong_print else 1]
            self._memo[at] = digest(tool.name, tool.code if s.code_in_key else None, params, self.chunk,
                                    tuple(self.key(r) for r in node.reads),
                                    self.key(node.cut_by) if node.cut_by else None, footage)
        return self._memo[at]

    def size(self, name, chunk):
        return self.tools[self.nodes[name].tool].bytes_per_row * self.chunk


@dataclass
class Stats:
    asked: int = 0
    computed: int = 0
    unanswered: int = 0
    refused: int = 0
    peak: int = 0
    scrubs: list = field(default_factory=list)
    broken: list = field(default_factory=list)


class Ask:
    """`demand` of the contract: an address is answered from the store or computed, its inputs
    demanded first. In a `walk`, frame tools gain `speed` and a plane passing through is handed
    on without being held; `keep` sends what is made to disk whatever the policy thinks."""

    def __init__(self, world, store, profile, clock, stats):
        self.world, self.store, self.profile, self.clock, self.stats = world, store, profile, clock, stats
        self.speed, self.passing, self.decoded = 1, False, None

    def demand(self, name, chunk):
        value = self._value(name, chunk)
        if value != self.world.truth(name, chunk):
            self.stats.broken.append(("O1", name, chunk))
        return value

    def _value(self, name, chunk):
        value = self.store.get(Address(self.world.key(name), chunk))
        return self._compute(name, chunk) if value is None else value

    def _compute(self, name, chunk, keep=False):
        w, node = self.world, self.world.nodes[name]
        tool = w.tools[node.tool]
        reads = w.reads_of(name, chunk)
        sizes = [w.size(n, c) for n, c in reads]
        began = self.clock[0]   # an entry's cost is all the time its making took, its inputs' too
        live = w.size(name, chunk) + (max(sizes, default=0) if tool.kind == "whole" else sum(sizes))
        self.store.reserve(live)   # the output and the inputs alive at once, whoever else holds them
        try:
            for n, c in reads:
                self._value(n, c)
            self.stats.peak = max(self.stats.peak, self.store.held_bytes + self.store.reserved)
            rows = w.chunk * (len(reads) if tool.kind == "whole" else 1)
            seconds = rows * tool.ms_per_row / 1000 * self.profile.slow
            if tool.kind == "frame":
                seconds /= self.speed
            if not node.reads:
                if self.decoded != chunk * w.chunk:
                    seconds += w.seek_s * self.profile.slow
                self.decoded = (chunk + 1) * w.chunk
            self.clock[0] += seconds
            self.stats.computed += rows
        finally:
            self.store.release(live)
        passed = self.passing and self.store.worth and tool.bytes_per_row > PLANE
        self.store.put(Address(w.key(name), chunk), w.truth(name, chunk), w.size(name, chunk),
                       self.clock[0] - began, keep=keep, spare=passed)
        return w.truth(name, chunk)

    def look(self, name, row):
        """One row for a caller looking at it: read out of its chunk where the store has that,
        made alone and held in memory only where it does not."""
        return self._looked(name, row)

    def _looked(self, name, row):
        w = self.world
        if w.tools[w.nodes[name].tool].kind == "whole":
            return self._value(name, 0)
        chunk = row // w.chunk
        whole, alone = Address(w.key(name), chunk), Address(w.key(name), -1 - row)
        value = self.store.get(alone) if alone in self.store.held else None
        if value is None and self.store.covered(whole.key, [chunk]):
            got = self.store.get(whole)
            value = None if got is None else digest(got, row)
        if value is None:
            value = self._row(name, row, alone)
        if value != digest(w.truth(name, chunk), row):
            self.stats.broken.append(("O1", name, chunk))
        return value

    def _row(self, name, row, alone):
        w, node = self.world, self.world.nodes[name]
        tool = w.tools[node.tool]
        chunk = row // w.chunk
        reads = w.reads_of(name, chunk)
        began = self.clock[0]
        live = tool.bytes_per_row + sum(w.tools[w.nodes[n].tool].bytes_per_row for n, _ in reads)
        self.store.reserve(live)
        try:
            if tool.kind == "reach":
                for r in range(max(0, row - node.params["reach"]), min(w.rows, row + node.params["reach"] + 1)):
                    self._looked(node.reads[0], r)
            for n, c in () if tool.kind == "reach" else reads:
                if n == name or w.tools[w.nodes[n].tool].kind == "whole":
                    self._value(n, c)
                elif tool.kind == "stepped":
                    for r in range(chunk * w.chunk, row + 1):
                        self._looked(n, r)
                else:
                    self._looked(n, row)
            self.stats.peak = max(self.stats.peak, self.store.held_bytes + self.store.reserved)
            rows = row - chunk * w.chunk + 1 if tool.kind == "stepped" else 1
            seconds = rows * tool.ms_per_row / 1000 * self.profile.slow
            if not node.reads:
                ahead = -1 if self.decoded is None else row - self.decoded
                read = ahead * tool.ms_per_row / 1000 if 0 <= ahead <= AHEAD else w.seek_s
                seconds += read * self.profile.slow
                self.decoded = row + 1
            self.clock[0] += seconds
            self.stats.computed += rows
        finally:
            self.store.release(live)
        value = digest(w.truth(name, chunk), row)
        self.store.put(alone, value, tool.bytes_per_row, self.clock[0] - began, memory_only=True)
        return value

    def window(self, name, start, count):
        """Rows `start` to `start + count` of an uncut node as a window makes them, each as
        (value, whether it is exact). A row is exact when every row it reads lay inside the
        window, or past an end of the clip, and was exact; any other is the window's own, made of
        what the window had, and is kept under an address that holds the window's range."""
        seen = {}
        return [self._windowed(name, row, (start, count), seen) for row in range(start, start + count)]

    def _windowed(self, name, row, span, seen):
        if (name, row) in seen:
            return seen[name, row]
        w, node = self.world, self.world.nodes[name]
        tool, chunk = w.tools[node.tool], row // w.chunk
        alone, whole = Address(w.key(name), -1 - row), Address(w.key(name), chunk)
        apart = Address(f"{w.key(name)}@{span}", row)
        found = None
        if alone in self.store.held:
            found = self.store.get(alone), True
        elif self.store.covered(whole.key, [chunk]) and (got := self.store.get(whole)) is not None:
            found = digest(got, row), True
        elif apart in self.store.held:
            found = self.store.get(apart), False
        if found is None:
            inside = lambda r: span[0] <= r < span[0] + span[1]   # noqa: E731
            began, exact = self.clock[0], True
            if tool.kind == "reach":
                reach = node.params["reach"]
                for r in range(max(0, row - reach), min(w.rows, row + reach + 1)):
                    exact &= inside(r) and self._windowed(node.reads[0], r, span, seen)[1]
            else:
                for read in node.reads:
                    exact &= self._windowed(read, row, span, seen)[1]
                if tool.kind == "stepped" and row > 0:
                    exact &= inside(row - 1) and self._windowed(name, row - 1, span, seen)[1]
            seconds = tool.ms_per_row / 1000 * self.profile.slow
            if not node.reads:
                ahead = -1 if self.decoded is None else row - self.decoded
                seconds += (ahead * tool.ms_per_row / 1000 if 0 <= ahead <= AHEAD else w.seek_s) * self.profile.slow
                self.decoded = row + 1
            self.clock[0] += seconds
            self.stats.computed += 1
            value = digest(w.truth(name, chunk), row) if exact else digest("a window's", w.key(name), span, row)
            at = alone if exact or not w.scheme.window_apart else apart
            self.store.put(at, value, tool.bytes_per_row, self.clock[0] - began, memory_only=True)
            found = value, exact
        seen[name, row] = found
        return found

    def walk(self, name):
        self.speed, self.passing = min(self.profile.cores, WITHIN), True
        try:
            for chunk in self.world.chunks_of(name):
                self.stats.asked += self.world.chunk
                self.demand(name, chunk)
        finally:
            self.speed, self.passing = 1, False

    def checkpoint(self, mark, name):
        """Walk `name` and name its chunks as the checkpoint `mark`; the addresses named."""
        self.walk(name)
        addresses = [Address(self.world.key(name), c) for c in self.world.chunks_of(name)]
        def fill(address):
            if not self.store.to_disk(address):
                self._compute(name, address.chunk, keep=True)

        self.store.checkpoint(mark, self.world.snapshot(), addresses,
                              [self.world.size(name, a.chunk) for a in addresses], fill)
        return addresses


OPS = (("scrub", 30), ("walk", 8), ("edit", 10), ("edit draw", 4), ("code", 3), ("footage", 1),
       ("evict", 6), ("delete", 3), ("reopen", 4), ("crash", 3), ("other", 5), ("checkpoint", 3),
       ("restore", 3), ("race", 5), ("unmark", 2), ("window", 12))


def sequence(seed, length, world):
    """A user's doings as plain tuples made from the seed alone, so any of them can be left out."""
    rng, names = random.Random(seed), list(world.nodes)
    kinds = [k for k, n in OPS for _ in range(n)]
    out = []
    for _ in range(length):
        kind = rng.choice(kinds)
        out.append((kind, rng.choice(names), rng.randrange(world.chunks), rng.randrange(1000)))
    return out


def run(ops, profile, scheme, rows=1024):
    """Run `ops` on a fresh machine and return its Stats, the oracles' findings in `broken`."""
    clock, stats = [0.0], Stats()
    world, disk = World(rows, scheme), Disk(profile, clock)

    def opened(writer):
        store = Store(disk, profile.memory, profile.disk, writer, atomic=scheme.atomic, worth=scheme.worth, locked=scheme.locked)
        return store, Ask(world, store, profile, clock, stats)

    store, ask = opened("a")
    opens, marks = 0, {}
    for i, (kind, name, chunk, pick) in enumerate(ops):
        node = world.nodes[name]
        try:
            if kind == "scrub":
                kept = world.chunks_of(name)
                if kept:
                    start = clock[0]
                    stats.asked += world.chunk
                    ask.look(name, kept[chunk % len(kept)] * world.chunk + pick % world.chunk)
                    stats.scrubs.append(clock[0] - start)
            elif kind == "walk":
                ask.walk(name)
            elif kind == "window":
                if node.cut_by is None and world.tools[node.tool].kind != "whole":
                    start, count = (chunk * world.chunk + pick) % (world.rows - 40), 8 + pick % 32
                    first = ask.window(name, start, count)
                    if ask.window(name, start, count) != first:
                        stats.broken.append(("O7 a window twice", name, start))
                    for row, (value, exact) in zip(range(start, start + count), first):
                        if exact and value != digest(world.truth(name, row // world.chunk), row):
                            stats.broken.append(("O7 said exact", name, row))
                    ask.look(name, start)   # an exact ask at the window's edges, which O1 judges
                    ask.look(name, start + count - 1)
            elif kind in ("edit", "edit draw"):
                wanted = [p for p in node.params if (p in node.computed) == (kind == "edit")]
                if wanted:
                    node.params[wanted[pick % len(wanted)]] = pick % 60
                    world.changed()
            elif kind == "code":
                world.tools[node.tool].code += 1
                world.changed()
            elif kind == "footage":
                world.footage[0] = f"content-{pick}"
                world.changed()
            elif kind == "evict":
                for address in list(store.held)[: pick % 40]:
                    store.drop(address, "memory")
            elif kind == "delete":
                names = sorted(disk.files)
                for victim in names[pick % 7 :: 11]:
                    disk.delete(victim)
                store.forget()
                gone = store.gone()   # said gone, by name
                marks = {m: a for m, a in marks.items() if m not in gone}
            elif kind == "reopen":
                opens += 1
                store, ask = opened(f"a{opens}")
            elif kind == "crash":
                disk.crash_in = pick % 9
                try:
                    ask.walk(name)
                finally:
                    disk.crash_in = None
            elif kind == "other":   # a second process on the same folder, as a bare walk is
                opens += 1
                other_store, other = opened(f"b{opens}")
                other.walk(name)
            elif kind == "checkpoint":
                marks[f"mark-{i}"] = set(ask.checkpoint(f"mark-{i}", name))
            elif kind == "race":   # a walk or a checkpoint while another writer lets go of entries under it
                turns = random.Random(pick)
                opens += 1
                rival = opened(f"r{opens}")[0]

                def other():
                    roll = turns.random()
                    if roll > 0.3:
                        return
                    named = {a.name for a in rival.named()}
                    loose = sorted((n for n in disk.names("entries/") if n not in named), key=disk.age)
                    if not loose:
                        return
                    if roll < 0.05:
                        rival.drop(address_of(turns.choice(loose)), "disk")
                    else:   # it names the entry touched longest ago, the next this writer would let go of
                        address = address_of(loose[-1])
                        try:
                            rival.checkpoint(f"rival-{i}-{len(marks)}", world.snapshot(), [address],
                                             [disk.size(address.name) or 0], lambda a: None)
                            marks[f"rival-{i}-{len(marks)}"] = {address}
                        except Refused:
                            pass

                disk.meddle = other
                try:
                    if pick % 2:
                        marks[f"mark-{i}"] = set(ask.checkpoint(f"mark-{i}", name))
                    else:
                        ask.walk(name)
                finally:
                    disk.meddle = None
            elif kind == "unmark" and marks:
                mark = sorted(marks)[pick % len(marks)]
                store.release_checkpoint(mark)
                del marks[mark]
            elif kind == "restore" and marks:
                mark = sorted(marks)[pick % len(marks)]
                if store.manifest(mark) is None:   # the manifest itself was deleted
                    del marks[mark]
                    continue
                snapshot, addresses = store.manifest(mark)
                world.restore(snapshot)
                answers = snapshot[1] == world.made()   # else it is of other code or footage, and says so
                stats.unanswered += not answers
                good = {Address(world.key(name), c) for name in world.nodes for c in world.chunks_of(name)}
                before = stats.computed
                for address in addresses:
                    if (address in good or answers) and store.get(address) is None:
                        stats.broken.append(("O3", mark, address.chunk))
                if stats.computed != before:
                    stats.broken.append(("O3 computed", mark, 0))
        except Crash:
            opens += 1
            store, ask = opened(f"a{opens}")
        except Refused:
            stats.refused += 1
        if store.held_bytes > profile.memory or stats.peak > profile.memory:
            stats.broken.append(("O5", kind, i))
        for mark in store.gone():
            if mark in marks:
                stats.broken.append(("O3 gone", mark, i))
        if disk.used() > profile.disk:
            stats.broken.append(("O5 disk", kind, i))
        for entry in disk.names("entries/"):
            if disk.files[entry][0] == TORN and scheme.atomic:
                stats.broken.append(("O6", entry, i))
        if stats.broken:
            stats.broken = stats.broken[:1] + [("at op", i, kind)]
            break
    stats.seconds, stats.disk = clock[0], disk.used()
    return stats


def shrunk(ops, profile, scheme):
    """The shortest run of `ops` found, by leaving one out at a time, that still breaks an oracle."""
    i = 0
    while i < len(ops):
        fewer = ops[:i] + ops[i + 1:]
        if run(fewer, profile, scheme).broken:
            ops = fewer
        else:
            i += 1
    return ops


def torture(scheme, seeds, length=60, profile=PROFILES["laptop"]):
    world = World(1024, scheme)
    for seed in range(seeds):
        ops = sequence(seed, length, world)
        tight = replace(profile, disk=(1, 2, 4, 40)[seed % 4] * GB)
        stats = run(ops, tight, scheme)
        if stats.broken:
            least = shrunk(ops, tight, scheme)
            return seed, run(least, tight, scheme).broken, [(k, n, c) for k, n, c, _ in least]
    return None


def price(scheme, profile, footage="1080p", rows=108000):
    """What named stretches of use cost on `profile`: seconds of simulated time each, the scrubs'
    median and worst in ms, the most memory taken and the disk held at the end."""
    clock, stats = [0.0], Stats()
    world, disk = World(rows, scheme, footage), Disk(profile, clock)
    rng, out = random.Random(1), {}

    def opened():
        store = Store(disk, profile.memory, profile.disk, atomic=scheme.atomic, worth=scheme.worth, locked=scheme.locked)
        return store, Ask(world, store, profile, clock, stats)

    def timed(label, act):
        start = clock[0]
        try:
            act()
            out[label] = clock[0] - start
        except Refused as refused:
            out[label] = str(refused)

    def scrubs(name, count, spread):
        """`count` looks at rows of `name`, each within `spread` rows of the last, or anywhere."""
        kept, took = world.chunks_of(name), []
        has, row = set(kept), None
        for _ in range(count):
            row = None if row is None or spread is None else row + rng.randint(-spread, spread)
            if row is None or row < 0 or row // world.chunk not in has:
                row = kept[rng.randrange(len(kept))] * world.chunk
            start = clock[0]
            ask.look(name, row)
            took.append((clock[0] - start) * 1000)
        return took

    def build():
        took = []
        for round_ in range(20):
            world.nodes["motion"].params["span"] = round_
            world.changed()
            took += scrubs("motion", 5, 30)
        out["build: a scrub in ms, median / worst"] = (statistics.median(took), max(took))

    def revisit():
        took = scrubs("detect", 50, None)
        out["revisit: a scrub in ms, median / worst"] = (statistics.median(took), max(took))

    def nudge(level):
        world.nodes["detect"].params["level"] = level
        world.changed()
        ask.walk("track")

    store, ask = opened()
    timed("build a pipeline: 20 edits, 5 scrubs each", build)
    timed("first full walk of the tracks", lambda: ask.walk("track"))
    timed("revisit: 50 scrubs anywhere", revisit)
    timed("the same walk again", lambda: ask.walk("track"))
    timed("checkpoint the tracks", lambda: ask.checkpoint("kept", "track"))
    store, ask = opened()
    timed("reopened: walk the tracks", lambda: ask.walk("track"))
    timed("nudge detect, walk again", lambda: nudge(41))
    timed("nudge it a second time", lambda: nudge(42))
    timed("and a third", lambda: nudge(43))
    out["peak memory GB"], out["disk held GB"] = stats.peak / GB, disk.used() / GB
    return out


def show(cell):
    if isinstance(cell, tuple):
        return f"{cell[0]:.0f} / {cell[1]:.0f}"
    return cell[:40] if isinstance(cell, str) else f"{cell:.1f}"


def prices(footage="1080p", only=None):
    cols = [(p, label, Scheme(worth=worth)) for p in PROFILES.values() if only in (None, p.name)
            for label, worth in (("worth", True), ("lru", False))]
    table = [price(scheme, profile, footage) for profile, _, scheme in cols]
    print(f"{footage}, an hour at 30 rows a second; seconds unless said")
    print("| | " + " | ".join(f"{p.name} {label}" for p, label, _ in cols) + " |")
    print("|---|" + "---|" * len(cols))
    for row in table[0]:
        print(f"| {row} | " + " | ".join(show(t.get(row, "")) for t in table) + " |")


def main(seeds=200):
    schemes = {
        "contract": Scheme(),
        "contract, plain LRU and everything written": Scheme(worth=False),
        "code left out of the key (today)": Scheme(code_in_key=False),
        "footage print of size and ends (today)": Scheme(strong_print=False),
        "entries written in place": Scheme(atomic=False),
        "no lock about letting go and naming": Scheme(locked=False),
        "a window's rows kept as exact ones": Scheme(window_apart=False),
    }
    for label, scheme in schemes.items():
        found = torture(scheme, seeds)
        if found is None:
            print(f"{label}: no oracle broken over {seeds} seeds")
        else:
            seed, broken, least = found
            print(f"{label}: seed {seed} breaks {broken[0]}; least sequence {least}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["prices"]:
        prices(*sys.argv[2:4])
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
