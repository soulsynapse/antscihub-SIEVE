# SIEVE

Signal Isolation for Ethological Video Events (SIEVE) isolates behavior from
video using interpretable signal-processing filters rather than a trained
model.

## Setup

The project uses [uv](https://docs.astral.sh/uv/):

```powershell
uv sync --extra gui --group dev
```

Run the application and static checks without activating the environment:

```powershell
uv run sieve-gui
uv run pyright
uv run lint-imports
```

The checks cover static types and architectural import contracts. The previous
test suite has been removed and will be rederived later.

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
