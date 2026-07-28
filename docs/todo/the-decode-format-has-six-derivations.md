---
title: The decode format is a key input with six derivations
status: open
opened: 2026-07-28

gated_on: >
  nothing structurally — every site already has the object that should own the
  answer, and two of the six are on the render thread inside a timed span

reads:
  - src/sieve/pipeline/cache_key.py
  - src/sieve/pipeline/dag.py
  - src/sieve/pipeline/plan.py
  - src/sieve/gui/preview_runner.py
---

# The decode format is a key input with six derivations

`cache_key.source_key` hashes the decode format, and its docstring states the
safety property in one clause:

> `Dag.needs_chroma` derives it; nothing chooses it by hand, which is what stops
> the key and the reader disagreeing.

Nothing chooses it by hand. Six places derive it:

| site | expression |
|---|---|
| `cli/run_cmd.py:119` | `not dag.needs_chroma` |
| `cli/preview_cmd.py:135` | `not graph_needs_chroma(project.pipeline)` |
| `cli/materialize_cmd.py:77` | `not graph_needs_chroma(project.pipeline)` |
| `gui/document.py:449` | `not graph_needs_chroma(self._pipeline)` |
| `gui/preview_runner.py:393` | `not graph_needs_chroma(request.pipeline, ...)` |
| `gui/preview_runner.py:427` | `not graph_needs_chroma(request.pipeline, ...)` |

Plus two more that receive it as a bare `bool` and record in prose where it came
from: `gui/materialize_worker.py`'s field is documented as
"`not graph_needs_chroma(pipeline)` for the graph that will read the file", and
`gui/crop_binding.py` says it is "derived by the caller for the same reason".
`CropArtifact.backs` takes it as a parameter and compares it. A `bool` is the
one type that cannot carry its own provenance, and this particular `bool` is an
input to every cache key rooted in that source.

**The failure is not "somebody chooses by hand".** It is that six derivations
are six chances of being handed a *different graph*, and the derivation is
correct at each site in isolation. `preview_runner._reader_for` spends a
paragraph on precisely this failure — "a reader handing BGR to a graph keyed for
luma would fill the store with entries labelled as something they are not" —
and then re-derives the format two methods after `_source_for` derived it,
because there is nowhere to put the answer between them.

**The axis of change.** `pipeline/plan.py` is "everything about a run that is
knowable before a frame is decoded", and it exists so that the executor need not
invent what a run does. Which format the source is decoded in is exactly that,
and it is already the thing every one of those six sites is about to key
against. `ExecutionPlan` builds a `Dag` on the way to its keys, so the answer is
computed there already and thrown away.

## The shape, and the constraint that decides it

The obvious move — a `luma` property on `ExecutionPlan` — is right for the three
CLI commands and **too late for the GUI**, which is the whole of the design
work here. `PreviewSession._plan` builds the plan *per render*, after the reader
exists; `preview_runner` needs the format *before* it can build or rebuild the
reader the session will use. Adding `plan.luma` and leaving `preview_runner`
deriving its own would be a seventh derivation, not a fix.

Two candidate resolutions, and the item picks one on evidence rather than
carrying both:

1. **Derive once at submission and put it on `RenderRequest`.** The GUI thread
   already holds the pipeline when it decides to render, `document.decodes_luma`
   already exists there, and the render thread stops deriving anything. The
   `Dag` build moves off the render thread as a side effect. Cost: `RenderRequest`
   grows a field that must not drift from `request.pipeline`, which is the same
   class of invariant, moved.
2. **A cached derivation keyed on the pipeline**, so all six sites call one
   function and repeat calls are free. Cheaper diff, but it leaves six call
   sites and buys only the cost, not the single home.

Recommendation is (1) for the GUI plus `plan.luma` for the CLI, on the grounds
that they are answering the question at different times and a single home that
serves both would have to be the earlier one.

**Measure before assuming the cost half.** `graph_needs_chroma` is
`Dag.build(...).needs_chroma` — a full graph build with parameter validation —
run twice per render on the render thread, inside the interval published as
`full_preview_render`. Whether that is microseconds or milliseconds is not
recorded anywhere, and the correctness argument above stands on its own if it
turns out to be free. Take the number first and put it in `docs/findings/`
either way; a cost claim in an item body that nobody measured is the thing
`docs/todo/_TEMPLATE.md` asks to be flagged.

**What breaks if this is wrong.** Nothing loudly, which is the danger. A format
and a key that disagree produce a store full of correctly-shaped frames computed
from the wrong pixels, and the symptom is a preview that looks plausible. The
protection is that `source_key`'s field already exists and `tests/unit/
test_decode_format.py` already pins the format-to-key relation — so a change
that routes the derivation differently but keeps one answer stays covered, and a
change that produces two answers has to break that test to land.
