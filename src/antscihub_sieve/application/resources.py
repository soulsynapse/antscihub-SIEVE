from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


GIB = 1024**3
DEFAULT_CPU_RESULT_MEMORY_BYTES = 16 * GIB
DEFAULT_GPU_RESULT_MEMORY_BYTES = 6 * GIB


class ExecutionTarget(str, Enum):
    CPU = "cpu"
    GPU = "gpu"


@dataclass(frozen=True, slots=True)
class ExecutionResourcePolicy:
    cpu_result_memory_bytes: int = DEFAULT_CPU_RESULT_MEMORY_BYTES
    gpu_result_memory_bytes: int = DEFAULT_GPU_RESULT_MEMORY_BYTES

    def __post_init__(self) -> None:
        _positive_bytes(
            "cpu_result_memory_bytes", self.cpu_result_memory_bytes
        )
        _positive_bytes(
            "gpu_result_memory_bytes", self.gpu_result_memory_bytes
        )

    def result_memory_limit(self, target: ExecutionTarget) -> int:
        if target is ExecutionTarget.CPU:
            return self.cpu_result_memory_bytes
        if target is ExecutionTarget.GPU:
            return self.gpu_result_memory_bytes
        raise ValueError(f"Unsupported execution target: {target!r}")


def _positive_bytes(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer byte count")
