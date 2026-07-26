# SIEVE *(Signal Isolation for Ethological Video Events)*


AntSciHub SIEVE is a tool to filter out behaviors from video without the need for training. If there is a *pure signal* that can identify your behavior, SIEVE enables you to isolate that quickly.


## Detection, fast. Goals:

* **Time to first detection: ~30 seconds** from a raw video to a working filter.
* **Time to first annotated footage: ~2.5 minutes** for a 10 minute video.
* **Standard workflow:** Drag threshold → see detections shift → drag frequency band → see scalogram change → set block count → done.


## Development environment

Managed entirely by [uv](https://docs.astral.sh/uv/). Three files define it and all three are committed:

| File | Role |
|---|---|
| `pyproject.toml` | What the project depends on, declared loosely (`numpy>=2.0`) |
| `uv.lock` | The exact resolved versions of all 153 packages, cross-platform |
| `.python-version` | The interpreter uv builds the env against (3.11) |

The environment itself lives in `.venv/` and is disposable — delete it and `uv sync` rebuilds it identically from the lockfile. Never edit it, never commit it.

### Setup

```
uv sync --extra gui --group dev-gui
```

That's the whole thing. uv downloads Python 3.11 if it's missing, creates `.venv/`, installs the locked versions, and installs SIEVE itself in editable mode so `src/` edits take effect immediately.

### Running things

Prefix commands with `uv run` instead of activating the venv:

```
uv run pytest                  # test suite
uv run nox -s checks           # ruff + pyright + import contracts + pytest — the CI gate
uv run nox -s benchmark        # latency budget checks
uv run nox -s docs             # regenerate docs/*/.index.md from entry frontmatter
uv run python -c "import sieve"
```

`docs/completed-todo/` and `docs/findings/` hold one file per item, each with
YAML frontmatter and a `YYYY.MM.DD-` prefix. Their `.index.md` tables are
generated from that frontmatter by `tools/doc_index.py` — never edited by hand,
and `checks` fails when one is stale.

`uv run` re-syncs the env first if it has drifted from the lockfile, so you cannot accidentally run against a stale environment. Activating (`.venv\Scripts\activate`) still works and is what VSCode does — you just lose that guarantee.

### Changing dependencies

```
uv add scipy                   # runtime dependency
uv add --group dev pytest-cov  # dev tooling
uv remove scipy
```

These edit `pyproject.toml` and `uv.lock` together. **Do not use `uv pip install`** — it mutates `.venv/` without touching the lockfile, which is exactly the drift the lockfile exists to prevent. CI runs `uv sync --locked` and fails if `uv.lock` is out of date with `pyproject.toml`.

To pull in someone else's dependency changes after a `git pull`, run `uv sync` again.

### Extras and groups

Optional dependencies are split so headless machines don't drag in Qt:

- `--extra gui` — PySide6, napari, pyqtgraph. Needed for the desktop app; omitted on HPC nodes.
- `--extra gpu` — CuPy. Opt-in, requires CUDA 12.
- `--group dev` — test and lint tooling. Included by default; use `--no-dev` to skip.
- `--group dev-gui` — pytest-qt. Only needed to run the GUI tests.

