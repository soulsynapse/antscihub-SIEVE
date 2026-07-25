# Handoff: build the documentation voice checker

DONE: 2026.07.25

[INTENT] A self-contained brief for an agent that has not read this repository.
Everything needed is below; do not go read the `docs/` tree to understand the
task. The standard is already decided — this is implementation, not design.

Do this task first. `handoff-voice-rewrite.md` is the task that uses the tool
you are building, and it cannot start until this one is done.

---

## What you are building

One file: `tools/doc_voice.py`. Stdlib only. No new dependencies.

It scans the repository's markdown, reports every place the prose breaks the
voice standard below, and prints a report a human or an agent can work through
line by line.

Then one addition to `noxfile.py`: a `doc_voice` session that runs it. Copy the
shape of the existing `code_health` session exactly — same `venv_backend="none"`
argument, same structure. Read that session before writing yours.

## The voice standard you are enforcing

SIEVE's documentation is written in **descriptive voice, not imperative**. It
says what is true and why, not what the reader must do. Confidence levels are
marked with explicit tags.

The five epistemic tags, spelled exactly like this including the brackets:

```
[STABLE]  [ASSUMPTION]  [INTENT]  [STALE WHEN]  [OPEN QUESTION]
```

## The three checks

### Check 1 — absolutes

Flag these words wherever they appear in prose: `must`, `must not`, `never`,
`always`, `all`, `every`, `any`, `guarantee`, `guarantees`, `guaranteed`,
`ensure`, `ensures`, `impossible`, `cannot`, `no exception`, `without
exception`.

Report the file, the line number, the word matched, and the full line.

### Check 2 — imperative openers

Flag a sentence that begins with a bare verb. Detect it as: the first word of a
sentence is in this list, capitalized or not.

```
use, do, don't, ensure, avoid, prefer, run, add, keep, treat, make, write,
register, mark, store, provide, separate, retain, implement, create, remove,
call, set, put, follow, apply, check, verify, note, consider, remember
```

Also flag a sentence beginning with `Do not` or `Never`.

A sentence begins after `.`, `!`, `?`, a newline, or a list bullet (`-`, `*`,
or `1.`). Report file, line number, the opening word, and the full line.

### Check 3 — untagged runtime claims

Flag a **paragraph** that both:

1. contains at least one of these words — `decode`, `decoder`, `cache`,
   `worker`, `subprocess`, `thread`, `latency`, `executor`, `frame`, `GPU`,
   `import`, `imports`, `memory`, `process`, `render`, `ms`, `budget` — and
2. contains none of the five epistemic tags, and sits under a heading whose
   section contains none of them either.

A paragraph is a run of non-blank lines. A section runs from one `#`-heading to
the next heading of the same or higher level.

Report the file, the paragraph's first line number, and its first 100
characters.

## What to skip when scanning

Skip all of these — a false positive here makes the report untrustworthy, and
an untrustworthy report is worse than none:

- fenced code blocks (` ``` ` … ` ``` `) and indented code blocks (4+ spaces)
- inline code spans (backtick … backtick)
- link targets — the `(...)` half of `[text](target)`, and bare URLs
- YAML frontmatter at the top of a file
- markdown table *delimiter* rows (`| --- | --- |`), but **not** table content

## Which files to scan

Everything matching `docs/**/*.md`, plus `NOTES.md`, `README.md`, `AGENTS.md`,
and `SIEVE-HANDOFF.md` at the repository root.

Skip `docs/06-ops/LLM-wiki/` entirely — it is a vendored copy of another tree
and is not SIEVE's prose.

## Section-aware reporting — the part that matters most

ADR files (`docs/05-adr/ADR-*.md`) have `## Decision` and `## Consequences`
sections that are imperative *by genre*. Whether the voice rule reaches them is
an unresolved question in this project.

Do not exempt them. Do not silently skip them. **Report them in a separate
section of the output**, headed exactly:

```
## ADR Decision and Consequences sections (genre question unresolved)
```

Everything else goes in the main body of the report. Keeping the two apart is
the entire point: it lets a reader act on the settled cases without the
unsettled ones burying them, and it keeps the open question visible instead of
letting a silent exemption answer it by default.

## Command-line interface

```
python tools/doc_voice.py                 # markdown report to stdout, exit 0
python tools/doc_voice.py --json          # same findings as JSON, exit 0
python tools/doc_voice.py --gate          # exit 1 if the main body has findings
python tools/doc_voice.py --path docs/05-adr/ADR-001-use-pyside6-for-the-ui.md
```

`--path` may be repeated and scopes the scan to those files. The rewriting
agent will use it constantly to check one file at a time, so make sure it works
with a single file argument.

`--gate` exists but is not wired into `nox -s checks`. The corpus does not pass
yet; wiring it now would make the gate red on arrival. Say so in a comment.

## Report format

Group by file, then by check. Under each file print a line per finding as:

```
  line 42  [absolute]   must   | The executor must not block on the decoder.
```

End with a summary count per check and a total. When there are no findings in
the main body, say so explicitly rather than printing an empty section.

## What "done" looks like

- `python tools/doc_voice.py` runs and prints a report over the real corpus.
- `nox -s doc_voice` runs it.
- `python tools/doc_voice.py --path <one ADR>` scopes correctly to that file.
- `python tools/doc_voice.py --json` emits parseable JSON.
- `.venv/Scripts/python.exe -m ruff check .` passes.
- `.venv/Scripts/python.exe -m ruff format --check .` passes.
- `.venv/Scripts/python.exe -m pyright` passes.
- A code block containing the word `must` produces **no** finding. Test this
  deliberately before you call the task done — it is the check most likely to
  be quietly broken.

## Repository conventions to follow

- Python 3.11. `from __future__ import annotations` at the top of the module.
- Full type annotations on every function.
- Ruff line length is 100.
- Comments explain *why*, not *what*. Where you pick a threshold or a word
  list, say in a comment why that choice and not another. Match the comment
  density of `tools/code_health.py` — read it first; it is the model for this
  file in structure, tone, and how it treats a report as distinct from a gate.
- The interpreter is `.venv/Scripts/python.exe`. Use it directly.
- Do not run `git commit` or `git push`.

## What not to do

- Do not edit any `.md` file. This task builds the tool; the rewrite is
  separate and comes after.
- Do not add a dependency.
- Do not wire `--gate` into `nox -s checks`.
- Do not decide the ADR-genre question. Report it and leave it open.
