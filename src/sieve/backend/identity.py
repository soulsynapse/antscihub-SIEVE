"""Backend identity string for cache keys, mirroring `decode/identity.py`.

Two backends running the same kernel on the same frame can disagree in the low
bits — different SIMD paths, different FFT implementations, different rounding
in a resize. So a cache entry produced on one is not automatically usable by
the other, and the key has to say which produced it.

The exception is a filter that has declared `backend_agnostic`, which is the
claim that its kernels agree bit for bit. That claim removes this string from
the key; nothing here decides that, `cache_key` does.
"""

from __future__ import annotations

from functools import cache

import numpy as np

from sieve.backend.dispatch import Backend

#: Bumped by hand when this package changes how it dispatches or transfers in a
#: way that could change a kernel's output, independently of any library
#: version — the counterpart of `DECODE_POLICY_VERSION`.
BACKEND_POLICY_VERSION = 1

#: cupy is distributed under a CUDA-version-suffixed name, and which one is
#: installed is a property of the machine rather than of this project. Tried in
#: order so the unsuffixed source install wins when someone built it by hand.
_CUPY_DISTRIBUTIONS = ("cupy", "cupy-cuda12x", "cupy-cuda11x")


@cache
def backend_identity(backend: Backend) -> str:
    if backend is Backend.CPU:
        return f"cpu-numpy-{np.__version__}/policy-{BACKEND_POLICY_VERSION}"
    return f"gpu-cupy-{_cupy_version()}/policy-{BACKEND_POLICY_VERSION}"


def _cupy_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    for distribution in _CUPY_DISTRIBUTIONS:
        try:
            return version(distribution)
        except PackageNotFoundError:
            continue
    raise RuntimeError(
        "no cupy distribution is installed, so no GPU kernel can have run — "
        f"looked for {list(_CUPY_DISTRIBUTIONS)}"
    )
