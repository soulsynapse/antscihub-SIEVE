from __future__ import annotations

from functools import cache

import numpy as np

from sieve.backend.dispatch import Backend


BACKEND_POLICY_VERSION = 1


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
