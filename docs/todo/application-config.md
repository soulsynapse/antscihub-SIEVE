---
title: Application config, and where the boundary with Preferences falls
status: deferred
gated_on: >
  the first setting the CLI and the GUI both need to read — cache bounds and
  backend selection policy are the two candidates
reads:
  - src/sieve/gui/preferences.py
  - docs/SCAFFOLD.md
  - docs/ARCHITECTURE.md
---

# Application config, and where the boundary with Preferences falls

**Why not now.** SCAFFOLD reserves `core/config.py` for pydantic-settings with
CLI > env > file precedence, and there is nothing to put in it. The two
configuration surfaces that exist are `gui/preferences.py`, which holds machine
preferences in `QSettings` and is deliberately GUI-only per non-negotiable #2,
and Typer flags on the CLI. Neither wants a third source today.

**The decision, which is why this is an entry rather than a missing file.** The
boundary between the two is undrawn. `proxy_width` is a preference — it is a
statement about this machine's decode budget and must never travel with a
project. A cache size limit or a default backend preference is arguably the
same, and arguably app config that the CLI needs too and `QSettings` cannot
carry to a headless node. Drawing that line against zero settings would draw it
somewhere arbitrary, and the failure mode is the one preferences.py's module
docstring already warns about: a setting that travels to another machine as an
assertion about hardware it has never seen.

**What would make it the right time.** The first setting the CLI and the GUI
both need to read. **One of the two candidates withdrew 2026-07-27:** cache
bounds became *derived* rather than configured — docs/todo/resource-ledger.md
reads the machine's allocation and consumers declare shares of it, so there is
no cache-size number for a config file to carry, and carrying one would
reintroduce exactly the travelling-hardware-assertion failure this file warns
about. Backend selection policy remains the live candidate, downstream of the
deferred **GPU execution** (docs/todo/gpu-execution.md) item.

Read: `src/sieve/gui/preferences.py` module docstring, `docs/SCAFFOLD.md`
`core/config.py`, `docs/ARCHITECTURE.md` non-negotiable #2.
