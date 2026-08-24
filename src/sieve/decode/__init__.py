"""Getting pixels out of a file, and nothing else.

A route answers in rows and delivers the source form; what to do with the
result — crop it, keep it, hand it to a step — belongs above. The package holds
one real implementation with two constructors (`software`, `hardware`, which
differ in an open option), the pair of them raced and cached (`hybrid`), the
verdict store that keeps the race from being re-run (`probe`), and a route with
no file behind it (`fake`) that exists so everything above this layer can be
checked without footage.

Which route serves what is settled and not re-argued here: the probed hybrid
serves the uncut original, and every derived file — a proxy, a cut — is served
by the plain software route, because file choice dominates route choice
(`docs/findings/2026.08.21-decode-stack-best-combinations.md`). The approaches
that lost are recorded in `experiments/decode-experiments/explorer.py` and are
deliberately not carried across.

Nothing here caches a frame. A route with a cache in it is one whose measured
cost depends on what was asked before, which is the arrangement that made
"playback should not fill the scrub cache" a slogan rather than a rule. Holding
frames is `sieve.store`'s, and it holds them keyed by form.
"""

from __future__ import annotations

from sieve.decode.fake import FakeRoute
from sieve.decode.hybrid import HybridRoute
from sieve.decode.pyav import PyAVRoute, hardware, software
from sieve.decode.route import STEP_WITHIN, Route

__all__ = [
    "STEP_WITHIN",
    "FakeRoute",
    "HybridRoute",
    "PyAVRoute",
    "Route",
    "hardware",
    "software",
]
