# SIEVE

Signal Isolation for Ethological Video Events (SIEVE) isolates behavior from
video using interpretable signal-processing filters rather than a trained
model.

## Setup

The project uses [uv](https://docs.astral.sh/uv/):

```powershell
uv sync --extra gui --group dev --group dev-gui
```

Run the application, the tests, and the static checks without activating the
environment:

```powershell
uv run sieve-gui
uv run pytest
uv run pyright
uv run lint-imports
```

The three checks cover behaviour, static types, and architectural import
contracts.

## Tests

`tests/` is laid out by what a test needs rather than by what it covers, because
what it needs is what decides whether it can run:

| Directory | What lives there |
| --- | --- |
| `tests/unit` | Pure functions and models; no Qt, no decode, no disk |
| `tests/integration` | The CLI and the pipeline end to end, over synthetic video |
| `tests/gui` | Qt widgets and gestures; needs the `gui` extra and `pytest-qt` |
| `tests/property` | Hypothesis properties over the pure layer |
| `tests/bench` | `pytest-benchmark` budgets; timing-sensitive |

Fixtures are synthesized rather than committed — `tests/conftest.py` writes a
short video whose frame *n* is identifiable by its intensity, so a decode test
can assert which frame a seek landed on. Qt tests run under
`QT_QPA_PLATFORM=offscreen` unless a platform is already chosen, so
`$env:QT_QPA_PLATFORM = "windows"; uv run pytest tests/gui` is how you watch a
gesture test do what it says.

`--strict-markers` is on, so a marker has to be declared in `pyproject.toml`
before it can be used. `gui` carries the Qt requirement and is what
`uv run pytest -m "not gui"` skips to get the headless suite; `slow` is on a
single subprocess test; `cuda` is declared but unused, since no GPU kernel is
under test yet. `benchmark` comes from `pytest-benchmark` rather than from the
declaration list.

The suite runs on six `pytest-xdist` workers by default, grouped by module
(`--dist loadscope`), which takes it from ~20 s to ~8 s. Six rather than one per
core: the tests are individually short, so past six the per-worker cost of
importing Qt, numpy, and OpenCV outweighs the parallelism, and 32 workers is
slower than 6. `loadscope` rather than the default `load` because keeping a
module on one worker imports it once and builds the session video fixture once.

**The timing budgets do not run in parallel.** `tests/bench` asserts what a
machine can do, and five sibling workers make that a claim about the harness
instead, so `gate.py` skips a budget when it sees `PYTEST_XDIST_WORKER`. Take
them serially:

```powershell
uv run pytest tests/bench -n0
```

`-n0` is also the way to run anything serially without editing `addopts` — it
keeps the plugin loaded and asks it for zero workers.

## Commands

```powershell
uv run sieve inspect
uv run sieve inspect downsample
uv run sieve run arena.sieve.yaml --dry-run
uv run sieve run arena.sieve.yaml
uv run sieve-gui
```

The headless `sieve` command uses the base dependencies. The desktop
`sieve-gui` command requires the `gui` extra.

## Dependencies

Manage dependencies with uv:

```powershell
uv add scipy
uv add --group dev pyright
uv remove scipy
```
