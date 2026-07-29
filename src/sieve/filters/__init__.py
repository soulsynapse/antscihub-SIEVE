from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

from sieve.core.filter_base import FilterSpec
from sieve.core.filter_registry import REGISTRY


GUIDANCE_SUFFIX = ".md"


def discover() -> tuple[FilterSpec, ...]:
    for module in pkgutil.iter_modules(__path__, f"{__name__}."):
        if module.name.rpartition(".")[2].startswith("_"):
            continue
        importlib.import_module(module.name)
    return tuple(sorted(REGISTRY, key=lambda spec: spec.key))


def guidance_path(spec: FilterSpec) -> Path:
    module = sys.modules.get(spec.params_model.__module__)
    source = getattr(module, "__file__", None)
    if source is None:
        raise LookupError(
            f"{spec.filter_id} {spec.version} is defined in "
            f"{spec.params_model.__module__!r}, which has no file to find guidance beside"
        )
    return Path(source).with_suffix(GUIDANCE_SUFFIX)
