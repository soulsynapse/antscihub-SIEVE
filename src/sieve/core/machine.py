"""The machine is read once. Both resources, one home, importable headless.

Every consumer that declares a share of the machine declares it against a
reading from this module — `gui/concurrency.py` for the interactive session,
`decode/prefetch.py` for decode pools, and the CLI and HPC paths that have no
GUI at all. Two callers re-deriving "how much of this machine do I have" and
disagreeing is a slow job nobody can explain when the resource is cores, and
an OOM kill when it is memory; `resolve_workers` documents the first at
length, and the second is why `available_memory` lives beside
`available_cpus` rather than growing up independently somewhere in `gui/`.

Both functions report the **allocation, never the machine**. Inside a
container, a cgroup, or a job step, the machine's totals are exactly the
wrong answer: a process that sizes its caches against 512 GB of node while
holding a 16 GB `memory.max` is not slow, it is killed. The desktop case,
where allocation and machine coincide, falls out as the last resort rather
than being the assumption.

**Why memory reads the scheduler's environment when `resolve_workers`
deliberately does not.** That function dropped `SLURM_CPUS_PER_TASK` because
affinity and cgroups already answer for CPUs under the usual plugins and a
`--workers` flag exists for the rest. Memory has no affinity equivalent: when
no cgroup binds, the job's declared `--mem` exists *only* in the scheduler's
environment, there is no command-line surface for it on the GUI path, and the
cost of guessing is a kill rather than a queue. So the fallback order below
consults `SLURM_MEM_PER_NODE` — not as scheduler coverage (PBS, LSF, and SGE
configurations that neither set a cgroup nor these variables fall through to
physical, and that is a known gap, not a claim), but because it is the one
honest reading left where it applies.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

#: cgroup v1 reports "no limit" as a huge page-rounded sentinel near 2**63
#: rather than by omitting the file; anything this large is the sentinel, not
#: an allocation.
_CGROUP_V1_UNLIMITED = 1 << 60


def available_cpus() -> int:
    """CPUs this process may actually use, not the ones the machine has.

    `os.cpu_count()` reports the machine and is the wrong answer inside a cgroup,
    a container, or a job step pinned to a subset of a node — all three being the
    ordinary case on the hardware this is meant to run on. `sched_getaffinity` is
    the right answer and exists only on Linux, which is why the fallback is here
    rather than at the call site.
    """
    affinity = getattr(os, "sched_getaffinity", None)
    if affinity is not None:
        return max(len(affinity(0)), 1)
    return max(os.cpu_count() or 1, 1)


def available_memory(
    *,
    cgroup_mount: Path = Path("/sys/fs/cgroup"),
    proc_cgroup: Path = Path("/proc/self/cgroup"),
    environ: Mapping[str, str] | None = None,
) -> int:
    """Bytes this process may hold before something kills or pages it.

    Precedence, most binding first:

    1. A cgroup limit (v2 `memory.max`, v1 `memory.limit_in_bytes`) — the
       number that, exceeded, is an OOM kill and not a slowdown.
    2. The scheduler's declaration when no cgroup answers —
       `SLURM_MEM_PER_NODE`, else `SLURM_MEM_PER_CPU x available_cpus()`.
       Slurm normally imposes the cgroup too; this is the fallback for
       configurations that do not.
    3. Physical memory — the desktop case, where the allocation is the machine.

    The keyword arguments exist so tests can point the reader at fixture
    cgroup trees and environments; production callers pass nothing. On a
    platform with no `/proc` (Windows) steps 1 and 2 find nothing and step 3
    answers, which is also the honest reading there.
    """
    limit = _cgroup_memory_limit(cgroup_mount, proc_cgroup)
    if limit is not None:
        return limit
    declared = _scheduler_memory_limit(os.environ if environ is None else environ)
    if declared is not None:
        return declared
    return physical_memory()


def _cgroup_memory_limit(mount: Path, proc_cgroup: Path) -> int | None:
    """The tightest memory limit any enclosing cgroup imposes, or None.

    Walks from the process's own cgroup up to the mount root because a limit
    on an *ancestor* kills just as surely as one on the leaf — a job step's
    cgroup often carries `max` itself while the job-level parent holds the
    real number. Missing files, `max`, and the v1 unlimited sentinel are all
    "this level does not bind", not zero — an absent limit must not read as
    an empty allocation.
    """
    try:
        text = proc_cgroup.read_text(encoding="utf-8")
    except OSError:
        return None

    limits: list[int] = []
    for line in text.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        _, controllers, group_path = parts
        if controllers == "":
            base = mount  # v2 unified hierarchy: the one line reads `0::/path`
            filename = "memory.max"
        elif "memory" in controllers.split(","):
            base = mount / "memory"  # v1: the memory controller's own mount
            filename = "memory.limit_in_bytes"
        else:
            continue

        node = (base / group_path.lstrip("/")).resolve()
        base = base.resolve()
        while True:
            limits.extend(_read_limit_file(node / filename))
            if node == base or base not in node.parents:
                break
            node = node.parent

    return min(limits) if limits else None


def _read_limit_file(path: Path) -> list[int]:
    """The limit a cgroup file states, as a zero-or-one element list."""
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return []
    if not raw.isdigit():
        return []  # v2 spells "no limit" as the literal `max`
    value = int(raw)
    if value >= _CGROUP_V1_UNLIMITED:
        return []
    return [value]


def _scheduler_memory_limit(environ: Mapping[str, str]) -> int | None:
    """What the scheduler says the job step may hold, or None.

    Slurm denominates both variables in megabytes (binary, as Slurm counts
    them). A value that does not parse is treated as absent rather than
    guessed at — the next reading down is physical memory, which is at least
    a number that means something.
    """
    per_node = _parse_slurm_megabytes(environ.get("SLURM_MEM_PER_NODE"))
    if per_node is not None:
        return per_node
    per_cpu = _parse_slurm_megabytes(environ.get("SLURM_MEM_PER_CPU"))
    if per_cpu is not None:
        return per_cpu * available_cpus()
    return None


def _parse_slurm_megabytes(raw: str | None) -> int | None:
    """A Slurm memory value in bytes: digits, optionally suffixed K/M/G/T."""
    if raw is None:
        return None
    text = raw.strip().upper()
    scale = 1024**2  # bare digits are megabytes
    if text and text[-1] in "KMGT":
        scale = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}[text[-1]]
        text = text[:-1]
    if not text.isdigit():
        return None
    return int(text) * scale


def physical_memory() -> int:
    """The machine's installed RAM — the last resort, and the desktop answer.

    Public because it is a distinct honest reading, not an implementation
    detail: a test asserting the resolver fell through to the desktop case
    needs the desktop number to compare against.
    """
    if sys.platform == "win32":
        import ctypes

        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_uint32),
                ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("GlobalMemoryStatusEx failed")
        return int(status.ullTotalPhys)

    sysconf = getattr(os, "sysconf", None)
    if sysconf is not None:
        return int(sysconf("SC_PHYS_PAGES")) * int(sysconf("SC_PAGE_SIZE"))
    raise OSError("no way to read physical memory on this platform")
