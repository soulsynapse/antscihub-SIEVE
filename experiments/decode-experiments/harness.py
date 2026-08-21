"""What every decode experiment needs and none of them should decide twice.

Three things live here, and each is here because an experiment that answered it
for itself would be an experiment whose result could not be compared with the
one beside it.

**Provenance, attached rather than remembered.** A decode number means nothing
without the build, the machine and the file that produced it, and a result file
that leaves any of those to the reader is one that gets carried across a library
upgrade and quietly stops being true. So `Run` collects them at the top of every
experiment and writes them into the result, and `ffprobe` is asked about the
footage rather than a figure being written down here.

**Samples, not summaries.** `time_case` keeps every per-iteration duration it
took. A run that averaged forty because it ran at sixty and then stalled is a
different result from one that ran at forty throughout, and only the trace tells
them apart — which is the whole reason the contention experiment can say anything.
Quantiles are computed when a result is read, never at write time.

**A warm-up that is discarded and said so.** The first read of a file pays for
the open, the index and a cold page cache, and folding that into a per-frame
median is how a backend gets blamed for the filesystem.

Deliberately no plotting and no comparison logic. A result file is the artifact;
what to conclude from two of them is a reading, and a reading that lives in the
harness is one nobody can disagree with.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FOOTAGE = HERE.parents[1] / "video-tests"

#: Iterations kept in full before a result starts storing a decimated trace. The
#: cap exists so a long contention run does not write a megabyte of floats; it is
#: high enough that every experiment here stays under it at its default size.
SAMPLE_CAP = 4000


def probe(path: Path) -> dict[str, Any]:
    """What `ffprobe` says about a file, as the result's record of its input.

    Asked of the file rather than read from a note, because codec, resolution and
    frame rate decide which mechanism an experiment is even measuring, and the
    file on disk is the only authority on those. Size and mtime go in beside them
    so two results over "the same" path can be told apart when it was not.
    """
    fields = (
        "stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,nb_frames"
    )
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", fields,
            "-show_entries", "format=duration,size,bit_rate",
            "-of", "json", str(path),
        ],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    parsed = json.loads(out)
    stream = (parsed.get("streams") or [{}])[0]
    stat = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        **stream,
        **parsed.get("format", {}),
    }


def _versions() -> dict[str, str]:
    """Whatever decode libraries are importable, and what they are.

    Recorded even for the ones an experiment did not use: a result that names
    only the backend it exercised cannot answer "was the other one even
    installed" a year later, and that question is how a missing hardware path
    gets mistaken for a decode fact.
    """
    found: dict[str, str] = {}
    for name in ("av", "cv2", "numpy"):
        try:
            module = __import__(name)
        except ImportError:
            found[name] = "absent"
            continue
        found[name] = getattr(module, "__version__", "unknown")
    try:
        ffmpeg = subprocess.run(
            ["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE
        ).stdout.decode(errors="replace").splitlines()[0]
    except (OSError, subprocess.CalledProcessError):
        ffmpeg = "absent"
    found["ffmpeg"] = ffmpeg
    return found


def _machine() -> dict[str, Any]:
    import os

    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "python": sys.version.split()[0],
    }


def _sieve_rev() -> str:
    """The tree the experiment ran from, so a result can be placed in history."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True, stdout=subprocess.PIPE, cwd=HERE,
        ).stdout.decode().strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@dataclass
class Case:
    """One configuration measured, and every duration it produced."""

    name: str
    params: dict[str, Any]
    samples_ms: list[float]
    unit: str = "ms per frame"
    note: str = ""
    truncated: bool = False


@dataclass
class Run:
    """One experiment's worth of cases, and the world they were taken in."""

    experiment: str
    question: str
    footage: list[dict[str, Any]] = field(default_factory=list)
    cases: list[Case] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add_footage(self, *paths: Path) -> None:
        self.footage.extend(probe(p) for p in paths)

    def note(self, text: str) -> None:
        """Something the numbers cannot say for themselves.

        Used for what was skipped, what fell back, and what a case could not
        measure — a silently absent case reads as a case that came out equal.
        """
        self.notes.append(text)

    def write(self) -> Path:
        RESULTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = RESULTS / f"{self.experiment}-{stamp}.json"
        payload = {
            "experiment": self.experiment,
            "question": self.question,
            "when": datetime.now(timezone.utc).isoformat(),
            "sieve_rev": _sieve_rev(),
            "machine": _machine(),
            "versions": _versions(),
            "footage": self.footage,
            "notes": self.notes,
            "cases": [
                {
                    "name": c.name,
                    "params": c.params,
                    "unit": c.unit,
                    "note": c.note,
                    "truncated": c.truncated,
                    "n": len(c.samples_ms),
                    "samples_ms": c.samples_ms,
                }
                for c in self.cases
            ],
        }
        path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        return path


def time_case(
    run: Run,
    name: str,
    work: Callable[[], Iterable[Any]],
    params: dict[str, Any] | None = None,
    warmup: int = 3,
    unit: str = "ms per frame",
    note: str = "",
) -> Case:
    """Time each step of `work`, discarding a warm-up, and record every sample.

    `work` returns an iterable whose every step is one unit — a frame, a seek, a
    batch. The harness never decides what a unit is, because a seek experiment
    and a throughput experiment disagree about it and both are right.

    The warm-up is dropped rather than reported separately: what it measures is
    the open, the container index and a cold page cache, none of which is the
    thing being compared, and all of which land on whichever case happens to run
    first.
    """
    params = dict(params or {})
    params["warmup_discarded"] = warmup
    samples: list[float] = []
    steps = work()
    for index, _ in enumerate(steps):
        now = time.perf_counter()
        if index == 0:
            start = now
            continue
        samples.append((now - start) * 1000.0)
        start = now
    samples = samples[warmup:]
    truncated = len(samples) > SAMPLE_CAP
    if truncated:
        stride = len(samples) // SAMPLE_CAP + 1
        params["samples_before_decimation"] = len(samples)
        params["decimation_stride"] = stride
        samples = samples[::stride]
    case = Case(name, params, samples, unit=unit, note=note, truncated=truncated)
    run.cases.append(case)
    return case


def quantiles(samples: list[float]) -> dict[str, float]:
    """p50/p95/min/max, computed at read time and never stored.

    Here so the console line an experiment prints on the way past is the same
    arithmetic every reader does, not so results carry it.
    """
    if not samples:
        return {}
    ordered = sorted(samples)
    def at(q: float) -> float:
        return ordered[min(len(ordered) - 1, int(q * len(ordered)))]
    return {
        "min": ordered[0],
        "p50": at(0.50),
        "p95": at(0.95),
        "max": ordered[-1],
        "mean": sum(ordered) / len(ordered),
    }


def report(case: Case) -> None:
    """One line per case, so a run is readable while it is still going."""
    q = quantiles(case.samples_ms)
    if not q:
        print(f"  {case.name:<38} (no samples) {case.note}")
        return
    print(
        f"  {case.name:<38} n={len(case.samples_ms):>5}  "
        f"p50={q['p50']:8.3f}  p95={q['p95']:8.3f}  min={q['min']:8.3f}  "
        f"({case.unit})"
    )
