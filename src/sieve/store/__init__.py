"""What is held, and where. Nothing here decides what to ask for.

Three tiers with one shape between them: a store answers *have you got this
instant of this picture*, and *here it is*. It does not choose which store to
ask, in what order, or what to do when none of them can answer — that is the
ladder's, above this layer, and keeping it out is what lets a store be checked
by itself.

`resident` holds frames in memory under one byte budget, protecting whatever
the active declarations need and dropping the rest (ADR-0006). `spans` reads
frames back out of files, through an explicit record rather than a directory
listing. `chunks` adds the write side for the files this tree encodes itself,
published by rename so that presence means complete. `coverage` is the record
all of them are honest through.

Every one of them is keyed by `(form key, row)`. The form is not decoration: it
is which source pixels at what sampling in what format, and two consumers
wanting different pictures of one instant want different arrays. A store keyed
by row alone cannot say which picture it is holding, which is what forced the
explorers to wipe on a crop change and to keep no display cache at all.
"""

from __future__ import annotations

from sieve.store.build import (
    BATCH,
    REDIRECT,
    Batch,
    FFmpegLauncher,
    Launcher,
    ProxyBuilder,
    missing_batches,
    next_batch,
    should_redirect,
)
from sieve.store.chunks import CHUNK_ROWS, ChunkStore
from sieve.store.coverage import Coverage, Span
from sieve.store.resident import NEAR_RADIUS, ResidentStore
from sieve.store.spans import SpanStore

__all__ = [
    "BATCH",
    "CHUNK_ROWS",
    "REDIRECT",
    "Batch",
    "FFmpegLauncher",
    "Launcher",
    "ProxyBuilder",
    "missing_batches",
    "next_batch",
    "should_redirect",
    "NEAR_RADIUS",
    "ChunkStore",
    "Coverage",
    "ResidentStore",
    "Span",
    "SpanStore",
]
