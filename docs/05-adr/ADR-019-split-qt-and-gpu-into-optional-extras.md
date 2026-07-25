# ADR-019: Split Qt and the GPU backend into optional extras

Reference for Architecture Decisions Record: https://docs.arc42.org/section-9/

## Context

ADR-012 selected uv and Hatchling and fixed the shape of `pyproject.toml`. It
did not say which packages belong in `[project] dependencies` and which belong
in `[project.optional-dependencies]`, because at the time nothing had been
installed against it.

`ARCHITECTURE.md` §3 states that the layer model is "the mechanism that makes
CLI and HPC parity real rather than aspirational" — a headless run reaches the
same executor the GUI drives. ADR-016 states the same property for the GPU
backend from the other direction: the controller imports and runs without CuPy
or CUDA present. Both are guarantees about what a process can do without a
package installed, and a dependency list that installs those packages anyway
makes the guarantees untestable rather than false. Nothing would fail; the
property would simply stop being observed.

[STABLE] The forcing case arrived from the test tooling rather than from the
runtime. `pytest-qt` is a plugin, and a plugin is imported at collection time.
In an environment with no importable Qt binding it errors during collection,
which aborts the whole session — not the Qt tests, the session. A `dev` extra
carrying `pytest-qt` therefore leaves a contributor who works on `core/`,
`pipeline/`, or the CLI unable to run any test at all on a machine with no Qt.
That is the parity guarantee failing at its most visible point: the person
whose work never touches a widget is the person blocked.

The same reasoning reaches one runtime dependency. `opencv-python` links a Qt
build for its `imshow` windows; `opencv-python-headless` does not. ADR-018
pins OpenCV as the decode path, so the base install would otherwise pull a Qt
into every headless run through the decoder.

## Decision

[STABLE] `dependencies` holds what a headless run needs, and nothing else. Qt,
the GPU backend, and the tooling that requires either are extras:

- `gui` — PySide6, napari, pyqtgraph (ADR-001).
- `gpu` — the CuPy CUDA wheel family (ADR-016). One CUDA variant per
  environment; the extra names the family and the environment picks the build.
- `dev` — the headless quality gate: Nox, Ruff, Pyright, import-linter,
  pytest, pytest-benchmark, Hypothesis, and the profilers. Installable and
  fully usable on a machine with no Qt and no CUDA.
- `dev-gui` — `antscihub-sieve[dev,gui]` plus `pytest-qt`. The only place
  `pytest-qt` appears.

[STABLE] `opencv-python-headless` rather than `opencv-python`, for the reason
above.

[INTENT] The rule that generates all four, and the thing to apply when a new
dependency arrives: a package belongs in `dependencies` when a CLI or HPC run
with no display and no GPU would fail without it. Everything else is an extra
named for the capability it adds.

The verification that this is real rather than declared is that `nox -s checks`
builds its environment from `dev` alone, and `tests/test_smoke.py` asserts in a
subprocess that no headless layer pulls in a Qt binding. A `checks` run in an
environment where Qt is installed would pass whether or not the split held.

## Status

Accepted.

## Consequences

- A contributor who never opens the GUI installs `dev` and runs the full
  default gate. This is the case the split exists to protect.
- GUI work requires the extra step of `dev-gui`, and a `qt`-marked test in an
  environment installed from `dev` is not silently skipped — it is not
  collected, because `nox -s test_gui` is the session that installs the binding
  and selects the marker (ADR-008, ADR-009).
- Four extras is more surface than one, and a contributor can install the wrong
  one. [ASSUMPTION] The failure is loud and self-describing — a missing import
  names the package — which is judged cheaper than a headless developer who
  cannot start pytest.
- `dev-gui` depends on the distribution's own name, so a rename of
  `antscihub-sieve` breaks it in a way that a flat list would not.
- ADR-001 requires the napari embedding to be revalidated against PySide6
  before first production use. The `gui` extra names PySide6 while the working
  environment carries PyQt6, so installing the extra is the point at which that
  revalidation becomes possible — see `NOTES.md`.

## Alternatives considered

### One `dev` extra containing everything

The conventional shape, and the one that produced the forcing case. It makes a
headless developer's pytest session abort at collection, and it makes the
`checks` gate run in an environment where Qt is importable, which retires the
only test of the parity guarantee.

### An `all` extra as the documented default

Installing everything by default and treating the split as advisory. It keeps
the extras honest in metadata while making the tested configuration the one
almost nobody runs, which is the same failure with a longer fuse.

### Qt as a hard dependency

Defensible if the GUI were the only entry point. It is not: `ARCHITECTURE.md`
§3 and the HPC handoff in §5 both assume a run with no display, and ADR-006
gives the CLI its own configuration surface. Making Qt mandatory would forbid
the deployment target rather than merely complicate it.

### Environment markers instead of extras

Conditioning Qt on the platform or on a display variable. Markers resolve at
install time from the machine's properties, and the distinction here is the
user's intent for that install — a headless CI box and a developer laptop
running the CLI want the same thing for different reasons. An extra is the
mechanism that expresses intent; a marker guesses at it.

### Leaving it undecided

The status quo before this ADR: a correct `pyproject.toml` with no record of
why. `NOTES.md` flagged that a later reader would look for an ADR to explain
the split and find only a comment. [INTENT] This ADR is cheap, and the
archaeology it prevents is not.

## References

- [SIEVE architecture: layer model](../04-architecture/ARCHITECTURE.md#3-layer-model)
- [ADR-001: Use PySide6 for the user interface](ADR-001-use-pyside6-for-the-ui.md)
- [ADR-008: Use pytest, Hypothesis, and pytest-benchmark](ADR-008-use-pytest-hypothesis-and-pytest-benchmark.md)
- [ADR-009: Use Nox for task orchestration](ADR-009-use-nox-for-task-orchestration.md)
- [ADR-012: Use uv and Hatchling for packaging](ADR-012-use-uv-and-hatchling-for-packaging.md)
- [ADR-016: Use CuPy as the only v1 GPU backend](ADR-016-use-cupy-as-the-only-v1-gpu-backend.md)
- [ADR-018: Pin OpenCV VideoCapture as the v1 decode path](ADR-018-pin-opencv-videocapture-as-the-v1-decode-path.md)
- [pytest-qt: Qt binding detection](https://pytest-qt.readthedocs.io/en/latest/troubleshooting.html)
