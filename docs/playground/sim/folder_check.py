"""Seeded doings of two stores over one real folder, checked against a plain dict of what each
address must hold. Run: python docs/playground/sim/folder_check.py [seeds]. It writes under a
temporary folder and removes it.
"""
import os
import random
import shutil
import sys
import tempfile
from pathlib import Path

sys.path[:0] = [str(Path(__file__).parent), str(Path(__file__).parents[3])]
from sieve_player.result_folder import Folder  # noqa: E402
from sieve_player.result_store import ENTRIES, PARTS, Address, Refused, Store  # noqa: E402

BUDGET, MEMORY = 200_000, 60_000


def check(seed, steps=300):
    """The first thing found wrong over `steps` doings of seed `seed`, or None."""
    rng, root = random.Random(seed), tempfile.mkdtemp(prefix="sieve-folder-")
    clock = [1_000_000.0]
    try:
        def opened(writer):
            return Store(Folder(root, writer, now=lambda: clock[0], wait=lambda s: None), MEMORY, BUDGET, writer, worth=False)

        stores, truth, marks, n = [opened("a"), opened("b")], {}, {}, 0
        for step in range(steps):
            clock[0] += rng.choice((0.1, 1, 90))
            store = rng.choice(stores)
            address = Address(f"k{rng.randrange(12)}", rng.randrange(6))
            does = rng.choice(("put", "put", "get", "get", "checkpoint", "release", "drop", "reopen", "tear", "part", "forget"))
            if does == "put":
                truth.setdefault(address, os.urandom(rng.randrange(100, 9000)))
                store.put(address, truth[address], len(truth[address]), cost=1.0)
            elif does == "get":
                got = store.get(address)
                if got is not None and got != truth.get(address):
                    return f"seed {seed} step {step}: {address} read back as another value"
            elif does == "checkpoint":
                named = [a for a in rng.sample(sorted(truth), min(len(truth), 3))]
                n += 1
                try:
                    store.checkpoint(f"m{n}", {}, named, [len(truth[a]) for a in named],
                                     lambda a: store.put(a, truth[a], len(truth[a]), keep=True))
                    marks[f"m{n}"] = named
                except Refused:
                    pass
            elif does == "release" and marks:
                store.release_checkpoint(marks.popitem()[0])
            elif does == "drop":
                store.drop(address)
            elif does == "reopen":
                stores[rng.randrange(2)] = opened(rng.choice("ab") + str(step))
            elif does == "tear":   # a file cut short, as a power loss leaves it; never one a checkpoint names
                path = os.path.join(root, *address.name.split("/"))
                if os.path.exists(path) and not any(address in named for named in marks.values()):
                    with open(path, "r+b") as f:
                        f.truncate(rng.randrange(0, max(1, os.path.getsize(path))))
                    for s in stores:
                        s.forget()
            elif does == "part":   # what a crash between a write and its rename leaves
                os.makedirs(os.path.join(root, PARTS.rstrip("/")), exist_ok=True)
                with open(os.path.join(root, PARTS.rstrip("/"), f"crashed-{step}"), "wb") as f:
                    f.write(os.urandom(5000))
            else:
                store.forget()
            for mark, named in marks.items():
                for a in named:
                    if stores[0].disk.read(a.name) is None:
                        return f"seed {seed} step {step} ({does}): checkpoint {mark} has lost {a}"
            real = sum(os.path.getsize(os.path.join(at, f)) for at, _, fs in os.walk(os.path.join(root, ENTRIES.rstrip("/"))) for f in fs)
            if real > BUDGET * 1.25:
                return f"seed {seed} step {step} ({does}): entries hold {real} bytes of a budget of {BUDGET}"
        return None
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    for seed in range(seeds):
        wrong = check(seed)
        if wrong:
            print(wrong)
            break
    else:
        print(f"nothing wrong over {seeds} seeds")
