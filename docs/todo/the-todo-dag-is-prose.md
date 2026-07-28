---
title: The todo DAG exists, in prose, where nothing can read it
status: open
opened: 2026-07-28

gated_on: >
  nothing structurally — the frontmatter and the index tool are already the
  shape this needs, and the edges are already written, in sentences

reads:
  - tools/doc_index.py
  - tests/docs/test_todo_hygiene.py
  - docs/todo/headless-detection.md
  - docs/todo/hpc-handoff-and-review-mode.md
  - docs/ASPIRATIONS.md
---

# The todo DAG exists, in prose, where nothing can read it

`docs/todo/headless-detection.md` contains this sentence:

> It also quietly falsifies a premise the deferred HPC item rests on
> (docs/todo/hpc-handoff-and-review-mode.md): "HPC is not a special path, it
> consumes the same serialized DAG the CLI does." True of the executor, not
> true of detection, **and the item does not know that yet.**

That is the whole argument for this item, stated by an existing file about
another existing file. The relation is real, it is load-bearing, and it is
visible from exactly one end. A reader who opens the HPC item — the one whose
premise is false — learns nothing, because an edge written as a sentence points
only the way the sentence runs.

It is not the only one. Transcribing what is already asserted in `gated_on`
lines and bodies:

| item | depends on |
|---|---|
| `qt-free-logic-under-gui` | `headless-detection` ("do it first") |
| `hpc-handoff-and-review-mode` | `headless-detection` (premise) |
| `replicate-status-columns` | `sink-writers`, `materialization` |
| `click-through-navigation` | `materialization` |
| `cache-eviction` | `materialization` |
| `sink-writers` | `materialization` |
| `pipeline-editor-list-or-graph` | `kernel-protocol-beyond-one-frame` |
| `downsample-or-rescale` | `parity-comparison-finding` |
| `application-config` | `gpu-execution` |
| `accuracy-feedback` | `annotation-spans` |
| `ledger-measurements` | `ledger-producers` *(completed)* |
| `adaptive-worker-allocation` | `ledger-producers` *(completed)* |

Twelve edges over thirty-four items, none of them checkable, several of them
recorded on one side only. `docs/.state.md` lists open items in file order and
deferred items in file order, which is the one ordering that carries no
information at all.

## The change

**`after:` is a new optional frontmatter key holding a list of slugs.**
`gated_on` stays exactly as it is and keeps its meaning. That division is the
only real design question here, and getting it wrong is what would make the
graph worse than the prose:

- **`after:` is a hard prerequisite that is another item.** The edge exists
  because doing this one first would produce work that has to be redone or a
  boundary that has to be designed twice.
- **`gated_on` is a trigger, which is usually not an item at all** — a
  measurement nobody has taken, a machine nobody owns, a filter nobody needs
  yet, a seated session with the v1 checkout. `profiling-as-a-module` waits on
  a budget miss; `block-signal-free-measures` waits on two decisions that are
  Kendrick's. Those have no edges and must not grow fake ones.

An item can have both, and several do: `replicate-status-columns` waits on
`sink-writers` **and** on somebody wanting the column. Do not collapse them —
an `after:` list that has drained does not make an item takeable, it makes it
*unblocked*, and the trigger is still the gate.

**Edges resolve across both directories.** A slug is looked up in
`docs/todo/<slug>.md` first and then in `docs/completed-todo/*-<slug>.md`,
because half the useful edges point at work that is done — that is what makes
the graph show a *frontier* rather than a backlog. `tools/complete_item.py`
moves the file and the slug survives the move, so nothing has to be rewritten
when an item completes. This is the property that makes the whole thing cheap,
and it is worth checking first: confirm the slug is recoverable from the
completed filename before writing the resolver against it.

**The gate is two assertions in `tests/docs/test_todo_hygiene.py`**: every slug
in an `after:` resolves to a file in one of the two directories, and the graph
has no cycle. Both are the kind of check this repo already trusts more than
prose — an unresolved slug is a renamed item nobody updated, and a cycle is two
items each claiming to come first, which today would simply sit there.

**The render goes in `docs/.state.md`**, and the graph is not the payload:

- **The frontier list is.** "Open items whose `after:` have all completed" is a
  derived answer to *what can I take right now*, and it is the one line of this
  work that changes how a session starts. It replaces a file-ordered list with
  a computed one.
- **A mermaid block is the artifact**, grouped into subgraphs by `serves:` so
  an aspiration and the chain walking toward it are one picture. Thirty-four
  nodes may render as hairball; if it does, keep the frontier list and cut the
  graph rather than tuning the layout. `tools/doc_index.py`'s `served_ids` and
  `aspiration_lines` are already the exact shape the subgraph pass needs, so
  this is an extension of a function that exists, not a new renderer.

## What this exposes, which is the point rather than a side effect

**`serves:` is on seven items of thirty-four.** Grouping by aspiration will
render four fifths of the tree as one undifferentiated blob, and the honest
response is to backfill `serves:` as part of this item — with the equally
honest outcome that many items serve nothing in `ASPIRATIONS.md` and should say
so by staying blank. `ASPIRATIONS.md` already says an aspiration with nothing
under it is the point of that block; the mirror case, a large body of work
under no aspiration, is the same signal pointing the other way, and a graph
that invented edges to avoid showing it would be the one failure mode that
makes this worse than what it replaces.

**Do not add a second edge kind in this item.** The tree holds at least one
relation that is a *conflict* rather than a prerequisite — a request whose
implementation would contradict a decision recorded elsewhere. It wants a
`conflicts_with:` eventually. It does not want one before `after:` has been
used on thirty-four items and shown what it costs, because two edge kinds
designed together are two guesses. (The instance this paragraph was written
against, `right-click-back-to-the-replicate-tab`, was folded into
`click-through-navigation` on 2026-07-28 — which is the cheap resolution when
a conflict edge would join two items and one of them holds nothing else, and
is worth trying before an edge kind is invented for it.)
