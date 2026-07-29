# SIEVE

Signal Isolation for Ethological Video Events (SIEVE) isolates behavior from
video using interpretable signal-processing filters rather than a trained
model.

## Setup

The project uses [uv](https://docs.astral.sh/uv/):

```powershell
uv sync --extra gui --group dev-gui
```

Run the application and checks without activating the environment:

```powershell
uv run sieve-gui
uv run pyright
uv run lint-imports
uv run pytest --benchmark-disable
uv run pytest -m benchmark --benchmark-only
```

The first three checks cover static types, architectural import contracts, and
behavior. The final command runs the performance budgets separately.

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
uv add --group dev pytest-cov
uv remove scipy
```
