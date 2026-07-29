from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

import psutil


_CGROUP_V1_UNLIMITED = 1 << 60


_CPU_SET_INFORMATION = 0
_CPU_SET_LOGICAL_INDEX = 14
_CPU_SET_EFFICIENCY_CLASS = 18


def available_cpu_ids() -> tuple[int, ...]:
    try:
        affinity = psutil.Process().cpu_affinity()
    except (AttributeError, NotImplementedError, psutil.Error):
        return tuple(range(max(os.cpu_count() or 1, 1)))
    return tuple(sorted(affinity)) or (0,)


def available_cpus() -> int:
    return max(len(available_cpu_ids()), 1)


def cpu_classes() -> dict[int, int]:
    allocation = set(available_cpu_ids())
    published = _published_cpu_classes()
    return {cpu: published.get(cpu, 0) for cpu in sorted(allocation)}


def _published_cpu_classes() -> Mapping[int, int]:
    if sys.platform == "win32":
        return _windows_cpu_classes()
    return linux_cpu_classes()


def _windows_cpu_classes() -> Mapping[int, int]:
    import ctypes
    kernel32 = ctypes.windll.kernel32
    needed = ctypes.c_ulong(0)
    kernel32.GetSystemCpuSetInformation(None, 0, ctypes.byref(needed), None, 0)
    if needed.value == 0:
        return {}
    buffer = (ctypes.c_ubyte * needed.value)()
    if not kernel32.GetSystemCpuSetInformation(
        buffer, needed.value, ctypes.byref(needed), None, 0
    ):
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


def linux_cpu_classes(
    root: Path = Path("/sys/devices/system/cpu"),
) -> Mapping[int, int]:
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
    ranked = {
        value: rank for rank, value in enumerate(sorted(set(capacities.values())))
    }
    return {cpu: ranked[value] for cpu, value in capacities.items()}


def available_memory(
    *,
    cgroup_mount: Path = Path("/sys/fs/cgroup"),
    proc_cgroup: Path = Path("/proc/self/cgroup"),
    environ: Mapping[str, str] | None = None,
) -> int:
    limit = _cgroup_memory_limit(cgroup_mount, proc_cgroup)
    if limit is not None:
        return limit
    declared = _scheduler_memory_limit(os.environ if environ is None else environ)
    if declared is not None:
        return declared
    return physical_memory()


def _cgroup_memory_limit(mount: Path, proc_cgroup: Path) -> int | None:
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
            base = mount
            filename = "memory.max"
        elif "memory" in controllers.split(","):
            base = mount / "memory"
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
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return []
    if not raw.isdigit():
        return []
    value = int(raw)
    if value >= _CGROUP_V1_UNLIMITED:
        return []
    return [value]


def _scheduler_memory_limit(environ: Mapping[str, str]) -> int | None:
    per_node = _parse_slurm_megabytes(environ.get("SLURM_MEM_PER_NODE"))
    if per_node is not None:
        return per_node
    per_cpu = _parse_slurm_megabytes(environ.get("SLURM_MEM_PER_CPU"))
    if per_cpu is not None:
        return per_cpu * available_cpus()
    return None


def _parse_slurm_megabytes(raw: str | None) -> int | None:
    if raw is None:
        return None
    text = raw.strip().upper()
    scale = 1024**2
    if text and text[-1] in "KMGT":
        scale = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}[text[-1]]
        text = text[:-1]
    if not text.isdigit():
        return None
    return int(text) * scale


class MemoryUnreadableError(OSError):
    pass


def process_memory_bytes() -> int:
    try:
        own = psutil.Process()
        total = own.memory_info().rss
        for child in own.children(recursive=True):
            total += child.memory_info().rss
    except psutil.Error as error:
        raise MemoryUnreadableError(
            f"session memory could not be read: {error}"
        ) from error
    return total


def physical_memory() -> int:
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
