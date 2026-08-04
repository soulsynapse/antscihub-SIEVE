"""The machine is read once. Both resources, one home, importable headless.

Every consumer that declares a share of the machine declares it against a
reading from this module — `core/shares.py` for the interactive session,
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

**Consequence for the HPC handoff, recorded here because this is where
somebody about to violate it is reading.** A generated job script declares
resources to the *scheduler* and nothing to SIEVE, because SIEVE reads what
the scheduler imposed. There is no `--memory` flag to generate, and adding one
should be read as a defect in this resolver rather than a feature of the
handoff. A job step is the friendliest case for this design — the allocation
is large and explicitly declared — and the least forgiving for any constant
chosen on a desktop, because exceeding a cgroup is an OOM kill.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

import psutil

#: cgroup v1 reports "no limit" as a huge page-rounded sentinel near 2**63
#: rather than by omitting the file; anything this large is the sentinel, not
#: an allocation.
_CGROUP_V1_UNLIMITED = 1 << 60

#: `SYSTEM_CPU_SET_INFORMATION.Type` for the only record kind defined, and the
#: byte offsets of the two fields read out of it. Named because three magic
#: numbers walking a byte stream is where this file would become unreadable.
_CPU_SET_INFORMATION = 0
_CPU_SET_LOGICAL_INDEX = 14
_CPU_SET_EFFICIENCY_CLASS = 18


def available_cpu_ids() -> tuple[int, ...]:
    """Logical CPU ids this process may run on, ascending.

    The ids, not the count, because `cpu_classes` has to say *which* CPUs are
    fast and a count cannot name one. `available_cpus` is `len` of this.

    `psutil` rather than `os.sched_getaffinity`, which exists only on Linux —
    and the gap was not theoretical: on Windows the affinity branch was
    unreachable and the fallback reported `os.cpu_count()`, so a process pinned
    to four cores sized its pools for thirty-two. `gui/concurrency.py`'s
    `fits_machine` documents itself as reading "the process's affinity or
    cgroup allocation", which was true on one of the two platforms this ships
    on. macOS has no affinity API at all and falls through to the machine,
    which is the honest reading there rather than a silent one: nothing can
    pin a thread, so nothing can be pinned away from.
    """
    try:
        affinity = psutil.Process().cpu_affinity()
    except (AttributeError, NotImplementedError, psutil.Error):
        return tuple(range(max(os.cpu_count() or 1, 1)))
    return tuple(sorted(affinity)) or (0,)


def available_cpus() -> int:
    """CPUs this process may actually use, not the ones the machine has.

    `os.cpu_count()` reports the machine and is the wrong answer inside a cgroup,
    a container, or a job step pinned to a subset of a node — all three being the
    ordinary case on the hardware this is meant to run on.

    **A count of CPUs is not a count of equal CPUs**, which is what every
    consumer of this number assumes. On a machine with more than one
    `cpu_classes` entry the same integer buys different throughput depending on
    which cores the scheduler hands out, and it hands out different ones over a
    process's life. This function keeps answering the question it was asked;
    `cpu_classes` is how a caller finds out the question was underspecified.
    """
    return max(len(available_cpu_ids()), 1)


def cpu_classes() -> dict[int, int]:
    """Performance class of each CPU in this process's allocation.

    Higher is faster, and the values are ordinal only — class 1 is quicker than
    class 0 by an amount nothing here claims. A machine whose cores are uniform
    reports every CPU in class 0, so `len(set(cpu_classes().values())) == 1` is
    the question "are my cores fungible", and it is the one `core/shares.py`'s
    constants silently assume the answer to.

    Read from the OS rather than inferred from a CPU model string: Windows'
    CPU-set API and Linux's `cpu_capacity` both publish this, and a table of
    model names would be wrong the week after it was written. Where neither
    answers — macOS, older kernels — every CPU reports class 0, which is the
    same shape as a uniform machine. That collapse is deliberate and it is a
    *reporting* limit, not a claim: Apple silicon has performance and
    efficiency cores this cannot see, so a caller must treat "one class" as
    "no evidence of more", never as proof of uniformity.

    Restricted to the allocation for `available_cpu_ids`' reason — a class map
    covering cores this process cannot run on would let a caller build an
    affinity set the OS refuses.
    """
    allocation = set(available_cpu_ids())
    published = _published_cpu_classes()
    return {cpu: published.get(cpu, 0) for cpu in sorted(allocation)}


def _published_cpu_classes() -> Mapping[int, int]:
    if sys.platform == "win32":
        return _windows_cpu_classes()
    return linux_cpu_classes()


def _windows_cpu_classes() -> Mapping[int, int]:
    """`GetSystemCpuSetInformation`'s efficiency class, per logical processor.

    The struct is walked by offset rather than declared as a `ctypes.Structure`
    because it is a variable-length record stream — each entry states its own
    `Size` and the union's shape depends on `Type` — so a fixed structure would
    have to assume a stride the API explicitly does not promise.

    Verified against measurement on the machine this was written on rather than
    against the documentation: efficiency class 1 was the set that binned the
    reference density surface in 84 ms and class 0 the set that took 145 ms, so
    "higher is faster" is a reading of the hardware and not of a sentence.
    """
    import ctypes

    kernel32 = ctypes.windll.kernel32
    needed = ctypes.c_ulong(0)
    kernel32.GetSystemCpuSetInformation(None, 0, ctypes.byref(needed), None, 0)
    if needed.value == 0:
        return {}
    buffer = (ctypes.c_ubyte * needed.value)()
    if not kernel32.GetSystemCpuSetInformation(buffer, needed.value, ctypes.byref(needed), None, 0):
        return {}

    raw = bytes(buffer)
    classes: dict[int, int] = {}
    offset = 0
    while offset + _CPU_SET_EFFICIENCY_CLASS < len(raw):
        size = int.from_bytes(raw[offset : offset + 4], "little")
        kind = int.from_bytes(raw[offset + 4 : offset + 8], "little")
        if size == 0:
            break
        if kind == _CPU_SET_INFORMATION:
            logical = raw[offset + _CPU_SET_LOGICAL_INDEX]
            classes[logical] = raw[offset + _CPU_SET_EFFICIENCY_CLASS]
        offset += size
    return classes


def linux_cpu_classes(root: Path = Path("/sys/devices/system/cpu")) -> Mapping[int, int]:
    """`cpu_capacity` ranked into ordinal classes, for big.LITTLE and friends.

    The kernel publishes a capacity number, not a class, and the number is
    normalised per-machine (the fastest core is 1024 by convention) — so it is
    comparable *within* a machine and meaningless across two. Ranking the
    distinct values discards a scale that never meant anything and keeps the
    ordering, which is the whole of what `cpu_classes` promises.

    Public for `physical_memory`'s reason — a distinct reading a test has to
    drive directly — and `root` is what lets it be driven, against a fixture
    tree. The Windows reader beside it stays private because there is no
    equivalent seam: it asks the kernel and there is nothing to point
    elsewhere, so it is exercised only on the platform it runs on.
    """
    capacities: dict[int, int] = {}
    try:
        entries = sorted(root.glob("cpu[0-9]*"))
    except OSError:
        return {}
    for entry in entries:
        try:
            raw = (entry / "cpu_capacity").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if raw.isdigit():
            capacities[int(entry.name[3:])] = int(raw)
    if not capacities:
        return {}
    ranked = {value: rank for rank, value in enumerate(sorted(set(capacities.values())))}
    return {cpu: ranked[value] for cpu, value in capacities.items()}


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


class MemoryUnreadableError(OSError):
    """A session memory reading that could not be taken honestly.

    Raised instead of returning a partial sum, because an undercounting
    memory readout is precisely the "looks better-founded than it is" failure
    ARCHITECTURE.md rule 6 names — it would be believed, and a reading that
    silently omitted a worker's memory would clear the ledger's ceiling while
    the machine swaps.
    """


def process_memory_bytes() -> int:
    """Resident bytes of this process and every live child, summed.

    The standing version of the ledger item's H3/H4 instrumentation: what a
    session actually holds, to be judged against what `core/shares.py`
    declares. RSS rather than private bytes because RSS is the quantity the
    OOM killer and the pager act on, and it is what the instrumented-session
    finding measured, so readings stay comparable with it.

    SIEVE spawns no child processes today, so the child walk is usually a
    walk over nothing — but it is taken every time rather than assumed away,
    because the process-isolation item will one day make it real and a sampler
    that quietly reported the parent alone from that day on is rule 6's
    failure with no symptom.

    Not cheap on Windows: enumerating children snapshots the process table.
    Callers sample from a worker thread (`gui/resource_probe.py` does), never
    from a thread with a latency budget.

    Raises:
        MemoryUnreadableError: if the process or any child cannot be read —
            permissions, or a worker exiting mid-sample. A child that exited
            probably holds nothing, but "probably nothing" summed into a
            total makes the total a guess, and the refusal is the honest
            report.
    """
    try:
        own = psutil.Process()
        total = own.memory_info().rss
        for child in own.children(recursive=True):
            total += child.memory_info().rss
    except psutil.Error as error:
        raise MemoryUnreadableError(f"session memory could not be read: {error}") from error
    return total


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
