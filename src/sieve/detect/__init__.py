"""Detection over an extracted series, below both front ends.

`DetectorSettings` is a first-class field on `Project` — serialized, versioned,
resolved per replicate, hashed — and until this package existed the one
function that turned it into an answer lived in `gui/chain_model.py`. Since
`sieve.gui` and `sieve.cli` are siblings in `.importlinter`'s layers contract,
that made a document declare a value only one front end could compute: rule 2
says the pipeline is a data structure and the complete input to rule 1's one
path, and that held for frames while failing for the thing frames are computed
*for*.

What crosses in is a *resolved* `DetectorSettings`, the collected `(T, B)`
series, `fps`, the series' start index, and `workers`. What does not cross is
`gui.chain_model.DetectorState` — the GUI's mutable tuning state, carrying a
soloed block the derivation provably never reads and a cheap/expensive tier
that is a scheduling concern — nor `Project`, because resolving one to a
`DetectorSettings` is `core/pipeline_model.py`'s job and already done. A
`Project` in a signature here would mean the extraction had failed.
"""

from __future__ import annotations

from sieve.detect.detector import DetectorUpdate, detect, gate_to, settled_for

__all__ = ["DetectorUpdate", "detect", "gate_to", "settled_for"]
