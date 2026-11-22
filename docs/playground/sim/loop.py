"""What a looping window costs, pass after pass, when what it shows is held as the tools' own
planes and when it is held as display proxies. Run: python docs/playground/sim/loop.py.

The pipeline and its prices are sim.py's; a proxy's bytes and milliseconds are proxyrate.py's on
this machine (a 1280x720 jpeg at 85). What a pass costs to paint a held plane is not measured and
is counted as nothing, which flatters the planes.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sim import GB, PROFILES, Disk, pipeline  # noqa: E402
from store import Address, Store  # noqa: E402

PROXY_BYTES = 70_000
PROXY_MAKE_MS = {"1080p": 2.2, "5.3K": 4.7}
PROXY_SHOW_MS = 2.0
FPS = 30


def lineage(nodes, name):
    """`name` and every node it is made from, upstream first."""
    out = []
    for read in nodes[name].reads:
        out += [n for n in lineage(nodes, read) if n not in out]
    return out + [name]


def loop(profile, footage, shown, rows, proxy, passes=6):
    """Seconds of the first pass, the median of the later ones, and the bytes held at the end."""
    tools, nodes, seek_s = pipeline(footage)
    clock = [0.0]
    store = Store(Disk(profile, clock), profile.memory, profile.disk)
    ms = lambda names: sum(tools[nodes[n].tool].ms_per_row for n in names) * profile.slow   # noqa: E731
    chain = [n for n in nodes if tools[nodes[n].tool].kind != "whole"]
    took = []
    for turn in range(passes):
        began, decoded = clock[0], None
        for row in range(rows):
            if turn == 0:
                clock[0] += ms(chain) / 1000
                decoded = row
            for name in shown:
                at = Address(f"{name}#shown", row)
                if store.get(at) is not None:
                    clock[0] += PROXY_SHOW_MS * profile.slow / 1000 if proxy else 0.0
                    continue
                cost = 0.0
                if turn:   # made again from the footage: the planes it is made from were not held
                    cost += ms(lineage(nodes, name)) / 1000 + (0.0 if decoded == row - 1 else seek_s * profile.slow)
                    decoded = row
                size = tools[nodes[name].tool].bytes_per_row
                if proxy:
                    cost += PROXY_MAKE_MS[footage] * profile.slow / 1000
                    size = PROXY_BYTES
                clock[0] += cost
                store.put(at, row, size, cost or 0.001, memory_only=True)
        took.append(clock[0] - began)
    return took[0], statistics.median(took[1:]), store.held_bytes


def main():
    print("| footage | machine | shown | loop | held as | first pass s | each later pass s | held GB |")
    print("|---|---|---|---|---|---|---|---|")
    for footage in ("1080p", "5.3K"):
        for profile in (PROFILES["laptop"], PROFILES["desktop"]):
            for shown in (("video",), ("video", "motion")):
                for seconds in (10, 30):
                    for proxy in (False, True):
                        first, later, held = loop(profile, footage, shown, seconds * FPS, proxy)
                        print(f"| {footage} | {profile.name} | {' + '.join(shown)} | {seconds} s | "
                              f"{'proxies' if proxy else 'planes'} | {first:.1f} | {later:.2f} | {held / GB:.2f} |")


if __name__ == "__main__":
    main()
