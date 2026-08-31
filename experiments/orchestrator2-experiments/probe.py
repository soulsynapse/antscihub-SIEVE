"""Which decoder each band opens, measured on this machine and remembered.

ADR-0020. Which route is faster is not a fact about the route: hardware decode
is ahead on a seek and behind on a sustained read, so a single verdict for it is
wrong in one direction or the other, and both findings that say so were taken on
one machine with one GPU.

**It probes arrangements, not routes, and that is the whole design.** Timing one
seek per route with nothing else running put hardware 14% ahead of software
here; the same pair measured while a sweep was running put it four times ahead
(`docs/findings/2026.08.31-a-hardware-interactive-reader-is-worth-four-times-more-in-place-than-alone.md`).
The gap is contention — two software decoders on one file destroy each other
(`docs/findings/2026.08.21-software-decoders-collapse-under-contention.md`) and
a GPU worker does not — so a probe that measured each route alone would recover
the 14%, conclude the pair was not worth having, and be wrong. This is FFTW's
planner rather than a benchmark suite: it times the plan it is about to run.

**The rule it picks by is a policy and is stated rather than measured.** Lowest
interactive seek latency wins, because that is the axis a person is waiting on;
sweep throughput breaks ties, because a fill nobody is watching may be slower so
long as it still finishes. A run that wants the other trade should read the
recorded numbers rather than the verdict, which is why both are cached.

**Cached per machine and per source shape**, and re-derived rather than
inherited when either changes — a checked-in route table is one machine's
verdicts made permanent and invisible, which is what ADR-0020 rejects. Delete
`probe-cache.json` to re-probe.
"""

from __future__ import annotations

import json
import platform
import random
import threading
import time
from pathlib import Path

import av

from fetch import Fetcher

CACHE = Path(__file__).resolve().parent / "probe-cache.json"

#: candidate routes, in the order a tie is broken. `None` is software.
ROUTES: tuple[str | None, ...] = (None, "cuda")
#: how much work one arrangement is timed over. Small because the probe is
#: paid at open and its job is to rank two arrangements, not to publish a
#: throughput figure — the findings already did that.
SEEKS = 10
STEPS = 40


def _shape(path: Path) -> str:
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        return (f"{stream.codec_context.name}"
                f"-{stream.codec_context.width}x{stream.codec_context.height}")


def _machine() -> str:
    return f"{platform.node()}-{platform.machine()}-{platform.system()}"


def _time_pairing(path: Path, sweep_route: str | None,
                  interactive_route: str | None, total: int) -> dict:
    """Seek latency on one band while the other sweeps, both open at once.

    The sweep is a real second decoder holding a real cursor, because the thing
    being measured is what the two cost each other. Timing the seeks with the
    sweep stopped is the microbenchmark this module exists to avoid.
    """
    stop = threading.Event()
    swept = {"n": 0}

    def sweep() -> None:
        reader = Fetcher(path, hwaccel=sweep_route)
        try:
            row = total // 4
            reader.exact(row)
            while not stop.is_set() and swept["n"] < STEPS * 4:
                row += 1
                reader.exact(row)
                swept["n"] += 1
        except Exception:
            pass
        finally:
            reader.close()

    hand = threading.Thread(target=sweep, daemon=True)
    hand.start()
    time.sleep(0.2)          # let the sweep reach a steady cursor

    rng = random.Random(4)
    seeks: list[float] = []
    reader = Fetcher(path, hwaccel=interactive_route)
    try:
        for _ in range(SEEKS):
            target = rng.randrange(total // 8, total - total // 8)
            started = time.perf_counter()
            reader.exact(target)
            seeks.append((time.perf_counter() - started) * 1000.0)
    finally:
        reader.close()
        stop.set()
        hand.join(5)

    seeks.sort()
    return {"sweep_route": sweep_route or "software",
            "interactive_route": interactive_route or "software",
            "seek_ms_p50": round(seeks[len(seeks) // 2], 2),
            "sweep_steps": swept["n"]}


def _measure(path: Path) -> dict:
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        total = stream.frames or int(
            stream.duration * stream.time_base * stream.average_rate)
    total -= 24

    pairings = []
    for sweep_route in ROUTES:
        for interactive_route in ROUTES:
            try:
                pairings.append(_time_pairing(path, sweep_route,
                                              interactive_route, total))
            except Exception as exc:
                #: a route this machine does not have is a fact about the
                #: machine and is recorded as one, not a reason to fail.
                pairings.append({"sweep_route": sweep_route or "software",
                                 "interactive_route":
                                     interactive_route or "software",
                                 "unavailable": repr(exc)})

    usable = [p for p in pairings if "unavailable" not in p]
    if not usable:
        return {"pairings": pairings, "sweep": None, "interactive": None}
    best = min(usable, key=lambda p: (p["seek_ms_p50"], -p["sweep_steps"]))
    return {"pairings": pairings,
            "sweep": None if best["sweep_route"] == "software"
            else best["sweep_route"],
            "interactive": None if best["interactive_route"] == "software"
            else best["interactive_route"]}


def routes(path: Path, refresh: bool = False) -> dict:
    """`{"sweep": route, "interactive": route}` for this machine and file.

    Probes and caches on a miss. `None` means software.
    """
    key = f"{_machine()}|{_shape(path)}"
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    if not refresh and key in cache:
        return cache[key]
    verdict = _measure(path)
    verdict["probed"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cache[key] = verdict
    CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return verdict


if __name__ == "__main__":
    import sys
    from harness import FOOTAGE  # noqa: E402

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        FOOTAGE / "GX010047c2_02_17_26.MP4")
    got = routes(target, refresh="--refresh" in sys.argv)
    for pairing in got["pairings"]:
        print(f"  sweep={pairing['sweep_route']:<9} "
              f"interactive={pairing['interactive_route']:<9} "
              + (f"seek p50 {pairing['seek_ms_p50']:>7} ms  "
                 f"sweep steps {pairing['sweep_steps']}"
                 if "unavailable" not in pairing
                 else f"unavailable: {pairing['unavailable'][:50]}"))
    print(f"\nverdict: sweep={got['sweep'] or 'software'}, "
          f"interactive={got['interactive'] or 'software'}")
