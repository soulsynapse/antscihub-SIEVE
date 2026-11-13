"""The machine, sampled: its memory, cores, disks and GPU as this process's and everything else's
against the whole, and the hard page faults, read through psutil and, for what psutil does not give
on Windows, the system's performance counters. `Machine.read()` is one sample in plain values and
`Watch` hands one a period to a sink that takes it as `Ledger.sample` does. Nothing of the player is
imported.
"""
import os
import sys
import threading
import time

import psutil

_COUNTERS = {"faults": r"\Memory\Page Reads/sec", "idle": r"\PhysicalDisk(_Total)\% Idle Time",
             "gpu": r"\GPU Engine(*)\Utilization Percentage"}

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _Value(ctypes.Structure):
        _fields_ = [("status", wintypes.DWORD), ("value", ctypes.c_double)]

    class _Item(ctypes.Structure):
        _fields_ = [("name", wintypes.LPWSTR), ("v", _Value)]

    _H, _DOUBLE = wintypes.HANDLE, 0x200
    _pdh = ctypes.WinDLL("pdh")
    _pdh.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(_H)]
    _pdh.PdhAddEnglishCounterW.argtypes = [_H, wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(_H)]
    _pdh.PdhCollectQueryData.argtypes = [_H]
    _pdh.PdhCloseQuery.argtypes = [_H]
    _pdh.PdhGetFormattedCounterValue.argtypes = [_H, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(_Value)]
    _pdh.PdhGetFormattedCounterArrayW.argtypes = [_H, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                                  ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]


class _Counters:
    """The performance counters of _COUNTERS under one query; a counter the system refuses reads None."""

    def __init__(self):
        self._q, self._c = _H(), {}
        if _pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._q)):
            self._q = None
            return
        for name, path in _COUNTERS.items():
            c = _H()
            if not _pdh.PdhAddEnglishCounterW(self._q, path, 0, ctypes.byref(c)):
                self._c[name] = c
        _pdh.PdhCollectQueryData(self._q)       # a rate is the change between two collections

    def read(self):
        """{"faults": a second, "idle": the disks' percent, "gpu": {instance: percent}}, each None where not read."""
        out = dict.fromkeys(_COUNTERS)
        if self._q is None or _pdh.PdhCollectQueryData(self._q):
            return out
        for name in ("faults", "idle"):
            v = _Value()
            if name in self._c and not _pdh.PdhGetFormattedCounterValue(self._c[name], _DOUBLE, None, ctypes.byref(v)):
                out[name] = v.value
        if "gpu" in self._c:
            size, n = wintypes.DWORD(0), wintypes.DWORD(0)
            _pdh.PdhGetFormattedCounterArrayW(self._c["gpu"], _DOUBLE, ctypes.byref(size), ctypes.byref(n), None)
            buf = ctypes.create_string_buffer(size.value)
            if size.value and not _pdh.PdhGetFormattedCounterArrayW(self._c["gpu"], _DOUBLE, ctypes.byref(size), ctypes.byref(n), buf):
                items = ctypes.cast(buf, ctypes.POINTER(_Item))
                out["gpu"] = {items[i].name: items[i].v.value for i in range(n.value)}
        return out

    def close(self):
        if self._q is not None:
            _pdh.PdhCloseQuery(self._q)
            self._q = None


class Machine:
    """`read()` is the machine since the read before, as plain values a dump and a saved history
    carry: "memory", [this process's resident bytes, everything else's in use, the machine's];
    "cores", [the cores this process kept busy, everything else kept busy, the machine's]; "disk",
    [the bytes a second this process read and wrote, everything else did, the share of the time the
    disks were busy]; "gpu", [this process's share of the busiest engine, everything else's of it];
    "faults", the disk reads a second that resolved hard page faults, anyone's. A process's bytes
    are every handle's, a socket's with a file's, so they are capped at the disks'. The busy share,
    "gpu" and "faults" are the performance counters' and None where there are none, off Windows or
    refused; the first read's rates are since the Machine was made."""

    def __init__(self):
        self._p, self._pid = psutil.Process(), f"pid_{os.getpid()}_"
        self._counters = _Counters() if sys.platform == "win32" else None
        self._was = self._now()

    def _now(self):
        cpu, disk, io, mine = psutil.cpu_times(), psutil.disk_io_counters(), self._p.io_counters(), self._p.cpu_times()
        return (time.perf_counter(), cpu.idle + getattr(cpu, "iowait", 0.0), mine.user + mine.system,
                disk.read_bytes + disk.write_bytes if disk else 0, io.read_bytes + io.write_bytes)

    def read(self):
        now, was = self._now(), self._was
        self._was = now
        dt = max(now[0] - was[0], 1e-6)
        n = psutil.cpu_count() or 1
        busy, mine = max(0.0, n - (now[1] - was[1]) / dt), (now[2] - was[2]) / dt
        disk = (now[3] - was[3]) / dt
        io = min((now[4] - was[4]) / dt, disk)
        mem, rss = psutil.virtual_memory(), self._p.memory_info().rss
        c = self._counters.read() if self._counters else dict.fromkeys(_COUNTERS)
        gpu = None
        if c["gpu"] is not None:
            engines = {}        # an engine of an adapter -> [this process's percent, everyone's]
            for name, v in c["gpu"].items():
                e = engines.setdefault(name.split("_luid_")[-1], [0.0, 0.0])
                e[0] += v * name.startswith(self._pid)
                e[1] += v
            ours, all_ = max(engines.values(), key=lambda e: e[1], default=[0.0, 0.0])
            gpu = [min(ours, 100.0) / 100, max(0.0, min(all_, 100.0) - ours) / 100]
        return {"memory": [rss, max(0, mem.total - mem.available - rss), mem.total],
                "cores": [min(mine, busy), max(0.0, busy - mine), n],
                "disk": [io, disk - io, None if c["idle"] is None else max(0.0, 100.0 - c["idle"]) / 100],
                "gpu": gpu, "faults": c["faults"]}

    def close(self):
        if self._counters:
            self._counters.close()


class Watch(threading.Thread):
    """Samples the machine every `period` seconds on its own thread into `sink("machine", value,
    t)`, t on the probe's clock, until `close()`."""

    def __init__(self, sink, period=1.0):
        super().__init__(name="machine", daemon=True)
        self._sink, self._period, self._stop_ = sink, period, threading.Event()
        self.start()

    def run(self):
        machine = Machine()
        while not self._stop_.wait(self._period):
            self._sink("machine", machine.read(), time.perf_counter())
        machine.close()

    def close(self):
        self._stop_.set()
        self.join()
