"""Backend registry: exactly ``cpu_numpy`` and ``gpu_cupy`` for v1 (ADR-016).

The absence of a Torch backend is intentional and tested. This layer imports
from ``core`` only.
"""
