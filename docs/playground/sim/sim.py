"""A simulated machine, pipeline and user for docs/playground/sim/store.py, and the oracles over them.

Time, disk and memory are simulated, so an hour's walk costs milliseconds and a seed replays a run.
What a tool would compute is a digest of everything it truly depends on (`World.truth`); what the
store is asked under is a key made by a scheme (`World.key`), so a scheme that leaves something out
of the key serves a wrong value and O1 sees it. Run: python docs/playground/sim/sim.py [seeds].
"""
import hashlib
import random
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from store import Address, Refused, Store  # noqa: E402

MB, GB = 1 << 20, 1 << 30
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


PROFILES = {   # placeholders until calibrated against docs/findings; see JOURNAL.md
    "laptop": Profile("laptop", 2, 2 * GB, 40 * GB, 100 * MB, 80 * MB, 0.010),
    "desktop": Profile("desktop", 16, 24 * GB, 500 * GB, 2000 * MB, 1500 * MB, 0.0002),
    "hpc": Profile("hpc", 64, 200 * GB, 5000 * GB, 300 * MB, 300 * MB, 0.005),
}


@dataclass(frozen=True)
class Scheme:
    """What is being tried: what a key holds, how an entry lands, how many rows a chunk is."""
    code_in_key: bool = True
    strong_print: bool = True
    atomic: bool = True
    chunk: int = 64


class Crash(Exception):
    pass


class Disk:
    """A folder as several stores see it, charging the clock for each read and write. A write is
    two steps, begun and whole; `crash_in` counts steps to a crash, which leaves a begun file torn."""

    def __init__(self, profile, clock):
        self.profile, self.clock, self.files, self.crash_in, self.ticks = profile, clock, {}, None, 0

    def _step(self):
        if self.crash_in is not None:
            self.crash_in -= 1
            if self.crash_in < 0:
                self.crash_in = None
                raise Crash()

    def write(self, name, value, size):
        self.files[name] = [TORN, size, self._tick()]
        self._step()
        self.clock[0] += size / self.profile.write_bps
        self.files[name][0] = value
        self._step()

    def rename(self, old, new):
        self.files[new] = self.files.pop(old)

    def read(self, name):
        if name not in self.files:
            return None
        value, size, _ = self.files[name]
        self.files[name][2] = self._tick()
        self.clock[0] += self.profile.seek_s + size / self.profile.read_bps
        return value, size

    def size(self, name):
        return self.files[name][1] if name in self.files else None

    def names(self, prefix):
        return [n for n in self.files if n.startswith(prefix)]

    def delete(self, name):
        self.files.pop(name, None)

    def touched(self, name):
        return self.files[name][2]

    def used(self):
        return sum(f[1] for f in self.files.values())

    def _tick(self):
        self.ticks += 1
        return self.ticks


@dataclass
class Tool:
    name: str
    kind: str            # "frame": a chunk of its inputs' same chunk; "stepped": and of its own chunk before; "whole": one chunk of all of its input's
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


def pipeline():
    tools = {t.name: t for t in (
        Tool("decode", "frame", 3.0, 6 * MB), Tool("gray", "frame", 1.0, 2 * MB),
        Tool("motion", "frame", 4.0, 2 * MB), Tool("energy", "frame", 0.5, 64),
        Tool("gate", "whole", 0.01, 16), Tool("detect", "frame", 12.0, 2 * MB),
        Tool("track", "stepped", 3.0, 512))}
    nodes = {n.name: n for n in (
        Node("video", "decode"), Node("gray", "gray", ("video",)),
        Node("motion", "motion", ("gray",), {"span": 2}, frozenset({"span"})),
        Node("energy", "energy", ("motion",)),
        Node("gate", "gate", ("energy",), {"keep": 20}, frozenset({"keep"})),
        Node("detect", "detect", ("gray",), {"level": 40, "outline": 1}, frozenset({"level"}), "gate"),
        Node("track", "track", ("detect",), {"reach": 8}, frozenset({"reach"}), "gate"))}
    return tools, nodes


class World:
    """The document, the tools' code and the footage as they are now."""

    def __init__(self, rows, scheme):
        self.tools, self.nodes = pipeline()
        self.rows, self.scheme = rows, scheme
        self.footage = ["content-0", "size-0"]   # what the file holds; what its size and ends say
        self.chunks = -(-rows // scheme.chunk)
        self._memo = {}

    def changed(self):
        self._memo.clear()

    def snapshot(self):
        return {n.name: dict(n.params) for n in self.nodes.values()}

    def restore(self, snapshot):
        for name, params in snapshot.items():
            self.nodes[name].params = dict(params)
        self.changed()

    def chunks_of(self, name):
        """The chunks a node has: one for a whole tool, those its gate keeps for a cut node."""
        node = self.nodes[name]
        if self.tools[node.tool].kind == "whole":
            return [0]
        if node.cut_by is None:
            return list(range(self.chunks))
        gate, keep = self.truth(node.cut_by, 0), self.nodes[node.cut_by].params["keep"]
        return [c for c in range(self.chunks) if int(digest(gate, c), 16) % 100 < keep]

    def reads_of(self, name, chunk):
        """The (node, chunk) pairs computing this chunk reads, its own chunk before among them."""
        node, out = self.nodes[name], []
        kind = self.tools[node.tool].kind
        for read in node.reads:
            if self.tools[self.nodes[read].tool].kind == "whole":
                out.append((read, 0))
            elif kind == "whole":
                out += [(read, c) for c in self.chunks_of(read)]
            else:
                out.append((read, chunk))
        if node.cut_by:
            out.append((node.cut_by, 0))
        if kind == "stepped":
            before = [c for c in self.chunks_of(name) if c < chunk]
            if before:
                out.append((name, before[-1]))
        return out

    def truth(self, name, chunk):
        at = ("truth", name, chunk)
        if at not in self._memo:
            node = self.nodes[name]
            tool = self.tools[node.tool]
            read = tuple(self.truth(n, c) for n, c in self.reads_of(name, chunk))
            params = tuple(sorted((k, v) for k, v in node.params.items() if k in node.computed))
            self._memo[at] = digest(tool.name, tool.code, params, read, chunk,
                                    None if node.reads else self.footage[0])
        return self._memo[at]

    def key(self, name):
        at = ("key", name)
        if at not in self._memo:
            node, s = self.nodes[name], self.scheme
            tool = self.tools[node.tool]
            params = tuple(sorted((k, v) for k, v in node.params.items() if k in node.computed))
            footage = None if node.reads else self.footage[0 if s.strong_print else 1]
            self._memo[at] = digest(tool.name, tool.code if s.code_in_key else None, params,
                                    tuple(self.key(r) for r in node.reads),
                                    self.key(node.cut_by) if node.cut_by else None, footage)
        return self._memo[at]

    def size(self, name, chunk):
        return self.tools[self.nodes[name].tool].bytes_per_row * self.scheme.chunk


@dataclass
class Stats:
    asked: int = 0
    computed: int = 0
    refused: int = 0
    peak: int = 0
    scrubs: list = field(default_factory=list)
    broken: list = field(default_factory=list)


class Ask:
    """`demand` of the contract: an address is answered from the store or computed, its inputs
    demanded first. `speed` is how many independent chunks are being worked at once."""

    def __init__(self, world, store, profile, clock, stats):
        self.world, self.store, self.profile, self.clock, self.stats = world, store, profile, clock, stats
        self.speed = 1

    def demand(self, name, chunk):
        w = self.world
        todo, order, seen = [(name, chunk)], [], set()
        while todo:   # everything not held that this chunk needs, inputs before readers
            at = todo.pop()
            if at in seen:
                continue
            seen.add(at)
            if self.store.covered(w.key(at[0]), [at[1]]):
                continue
            order.append(at)
            todo += w.reads_of(*at)
        for n, c in sorted(order, key=lambda at: (list(w.nodes).index(at[0]), at[1])):
            self._compute(n, c)
        return self._served(name, chunk)

    def _served(self, name, chunk):
        value = self.store.get(Address(self.world.key(name), chunk))
        if value is None:   # let go between the computing and the reading; made again
            self._compute(name, chunk)
            value = self.store.get(Address(self.world.key(name), chunk))
        if value is not None and value != self.world.truth(name, chunk):
            self.stats.broken.append(("O1", name, chunk))
        return value

    def _compute(self, name, chunk):
        w, tool = self.world, self.world.tools[self.world.nodes[name].tool]
        reads = w.reads_of(name, chunk)
        sizes = [w.size(n, c) for n, c in reads]
        live = w.size(name, chunk) + (max(sizes, default=0) if tool.kind == "whole" else sum(sizes))
        self.store.reserve(live)   # the output and the inputs alive at once, whoever else holds them
        try:
            for n, c in reads:
                if self.store.get(Address(w.key(n), c)) is None:
                    self._compute(n, c)
            self.stats.peak = max(self.stats.peak, self.store.held_bytes + self.store.reserved)
            rows = w.scheme.chunk * (len(reads) if tool.kind == "whole" else 1)
            self.clock[0] += rows * tool.ms_per_row / 1000 / self.speed
            self.stats.computed += rows
        finally:
            self.store.release(live)
        self.store.put(Address(w.key(name), chunk), w.truth(name, chunk), w.size(name, chunk))

    def walk(self, name):
        w = self.world
        upstream, todo = set(), [name]
        while todo:
            n = todo.pop()
            if n not in upstream:
                upstream.add(n)
                todo += list(w.nodes[n].reads) + ([w.nodes[n].cut_by] if w.nodes[n].cut_by else [])
        stepped = any(w.tools[w.nodes[n].tool].kind == "stepped" for n in upstream)
        self.speed = 1 if stepped else self.profile.cores
        try:
            for chunk in w.chunks_of(name):
                self.stats.asked += w.scheme.chunk
                self.demand(name, chunk)
        finally:
            self.speed = 1


OPS = (("scrub", 30), ("walk", 8), ("edit", 10), ("edit draw", 4), ("code", 3), ("footage", 1),
       ("evict", 6), ("delete", 3), ("reopen", 4), ("crash", 3), ("other", 5), ("checkpoint", 3),
       ("restore", 3))


def sequence(seed, length, world):
    """A user's doings as plain tuples made from the seed alone, so any of them can be left out."""
    rng, names = random.Random(seed), list(world.nodes)
    kinds = [k for k, n in OPS for _ in range(n)]
    out = []
    for _ in range(length):
        kind = rng.choice(kinds)
        out.append((kind, rng.choice(names), rng.randrange(world.chunks), rng.randrange(1000)))
    return out


def run(ops, profile, scheme, rows=4096):
    """Run `ops` on a fresh machine and return its Stats, the oracles' findings in `broken`."""
    clock, stats = [0.0], Stats()
    world, disk = World(rows, scheme), Disk(profile, clock)

    def opened(writer):
        store = Store(disk, profile.memory, profile.disk, writer, atomic=scheme.atomic)
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
                    stats.asked += scheme.chunk
                    ask.demand(name, kept[chunk % len(kept)])
                    stats.scrubs.append(clock[0] - start)
            elif kind == "walk":
                ask.walk(name)
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
                store.held.clear()
                store.held_bytes = 0
                for address in store.gone():
                    marks = {m: a for m, a in marks.items() if address not in a}   # said gone, by name
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
                ask.walk(name)
                addresses = [Address(world.key(name), c) for c in world.chunks_of(name)]
                store.checkpoint(f"mark-{i}", world.snapshot(), addresses)
                marks[f"mark-{i}"] = set(addresses)
            elif kind == "restore" and marks:
                mark = sorted(marks)[pick % len(marks)]
                if store.manifest(mark) is None:   # the manifest itself was deleted
                    del marks[mark]
                    continue
                snapshot, addresses = store.manifest(mark)
                world.restore(snapshot)
                good = {Address(world.key(name), c) for name in world.nodes for c in world.chunks_of(name)}
                before = stats.computed
                for address in addresses:
                    if address in good and store.get(address) is None:
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
    world = World(4096, scheme)
    for seed in range(seeds):
        ops = sequence(seed, length, world)
        stats = run(ops, profile, scheme)
        if stats.broken:
            least = shrunk(ops, profile, scheme)
            return seed, run(least, profile, scheme).broken, [(k, n, c) for k, n, c, _ in least]
    return None


def main(seeds=200):
    schemes = {
        "contract": Scheme(),
        "code left out of the key (today)": Scheme(code_in_key=False),
        "footage print of size and ends (today)": Scheme(strong_print=False),
        "entries written in place": Scheme(atomic=False),
    }
    for label, scheme in schemes.items():
        found = torture(scheme, seeds)
        if found is None:
            print(f"{label}: no oracle broken over {seeds} seeds")
        else:
            seed, broken, least = found
            print(f"{label}: seed {seed} breaks {broken[0]}; least sequence {least}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
