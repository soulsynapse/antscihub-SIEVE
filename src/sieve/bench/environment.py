"""Environment metadata for a benchmark run (ADR-008).

ADR-008 requires a benchmark result to carry enough about the machine, the
interpreter, the dependency versions, and the thread settings to say whether
two results are comparable, and forbids a single universal wall-time threshold
across heterogeneous developer machines. This module is what makes the first
half possible, and therefore what makes the second half enforceable later: a
gate can only compare like for like if the recorded metadata says what "like"
means.

[INTENT] Captured now, unused as a gate. A run recorded without metadata is
unusable retroactively -- the machine it ran on cannot be reconstructed after
the fact -- so the capture has to precede the comparison it will eventually
support, not follow it.

Qt-free and cheap. Nothing here imports a decoder, an array library, or a GUI
toolkit; version probes go through ``importlib.metadata``, which reads
installed distribution metadata rather than importing the package.
"""

from __future__ import annotations

import importlib.metadata
import os
import platform
import sys
import time
from typing import Any, Final

__all__ = ["THREAD_ENV_VARS", "TRACKED_DISTRIBUTIONS", "capture"]

# Distributions whose version changes a timing rather than a test outcome.
# Anything whose drift shows up as a failure does not need to be here; this is
# the set whose drift shows up only as a different number.
TRACKED_DISTRIBUTIONS: Final = (
    "antscihub-sieve",
    "numpy",
    "opencv-python-headless",  # ADR-018: the pinned decode path
    "pytest",
    "pytest-benchmark",
)

# Thread-pool settings dominate array and decode throughput and are set outside
# the process, so a result recorded without them cannot be reproduced even on
# the same machine. Recorded as absent rather than defaulted: "unset" and "set
# to the core count" are different states and the libraries treat them
# differently.
THREAD_ENV_VARS: Final = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "OPENCV_FFMPEG_THREADS",
)


def _distribution_versions() -> dict[str, str | None]:
    """Installed versions of the tracked distributions.

    A missing distribution records ``None`` rather than being omitted: an
    absent key is ambiguous between "not installed" and "this run predates the
    field", and only one of those two invalidates a comparison.
    """
    versions: dict[str, str | None] = {}
    for name in TRACKED_DISTRIBUTIONS:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _cpu() -> dict[str, Any]:
    return {
        "processor": platform.processor() or None,
        "machine": platform.machine() or None,
        "logical_cores": os.cpu_count(),
        # CPU frequency scaling makes a laptop's timings depend on thermal
        # state, which is exactly why ADR-008 rejects a universal threshold.
        # Recording the governor is out of reach portably; recording that the
        # host is a laptop-class machine is not, and is left to the operator.
        "host_label": os.environ.get("SIEVE_BENCH_HOST_LABEL") or None,
    }


def capture() -> dict[str, Any]:
    """A JSON-serializable snapshot of everything that makes results comparable.

    Flat-ish and plain: this ends up embedded in ``pytest-benchmark`` output
    and in report sidecars, both of which round-trip through JSON.
    """
    return {
        "schema_version": 1,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "platform": platform.platform(),
        "system": platform.system(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "cpu": _cpu(),
        "distributions": _distribution_versions(),
        "thread_env": {name: os.environ.get(name) for name in THREAD_ENV_VARS},
        # A benchmark run under a debugger, a tracer, or a coverage plugin is
        # not comparable with one that is not, and the difference is otherwise
        # invisible in the recorded numbers.
        "trace_hook_active": sys.gettrace() is not None,
    }
