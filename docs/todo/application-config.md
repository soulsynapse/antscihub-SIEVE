---
title: Application config, and where the boundary with Preferences falls
status: deferred
opened: 2026-07-27T15:01:34-07:00
priority: unassessed
gated_on: >
  the first setting the CLI and the GUI both need to read — backend selection
  policy is the only live candidate, since cache bounds withdrew 2026-07-27
  when the resource ledger made them derived rather than configured
reads:
  - src/sieve/gui/preferences.py
  - docs/SCAFFOLD.md
---

# Application config, and where the boundary with Preferences falls

`SCAFFOLD.md` reserves `core/config.py` for pydantic-settings with CLI > env >
file precedence. The two configuration surfaces that exist are
`gui/preferences.py` (machine preferences in `QSettings`, deliberately GUI-only
per rule 2) and Typer flags. Drawing the boundary between them against zero
settings would draw it somewhere arbitrary.

**The constraint that decides it**, and the reason this is an entry rather than
a missing file: the failure mode `preferences.py`'s docstring already names — a
setting that travels to another machine as an assertion about hardware it has
never seen. `proxy_width` is a preference for exactly that reason. Anything
that goes in `core/config.py` must be a statement about the *work*, never about
the machine; the machine is what the resource ledger reads.
