---
title: A stage header groups cards by nothing the tree declares
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k stage_header"
opened: 2026-08-09
---

# A stage header groups cards by nothing the tree declares

09.1 landed the card stack and left this clause of its own body unbuilt:
"stage headers with their `in -> out` chips between groups". The stack draws
one flat run of cards, because what a *stage* is has no answer in the tree.

The referent's `STAGES` is a hardcoded table of `(name, chip, members)`, and
[MOCKUP-MAP.md](../MOCKUP-MAP.md) puts its membership under "what the mockup
does not settle" — sample data standing in for a derivation. v2 is no better:
`gui/chain_model.py` declares `Stage`, `ChainKind` and a per-step `stage=` in a
hand-written `parity_chain`, and its `ChainKind` docstring says outright that it
is "deliberately not `core.filter_base.StreamKind`: that one cannot tell an
image from a block grid". So both referents assert the grouping rather than
deriving it, and copying either into `gui/chain_stack.py` is the per-tool table
that module exists without.

What v3 has that neither had is `ElementKind` and the fold that resolves it:
`Dag._elements` walks `tool_base.node_element` forward from `PIXEL`, and the
chain's grouping falls out of it exactly where v2 drew its headers — pixels
through pixels is the spatial prep, `block_signal` is where pixels become
blocks, `detect` is where blocks become a frame value. So the *chip* is
derivable and the group is a maximal run of nodes sharing one `(in, out)` pair.
Two things stand in the way, and they are the decision this item is for. The
fold lives behind `Dag.build`, which refuses a graph naming a tool this install
lacks — and the window has to draw exactly that graph (`gui/app.resolved_specs`,
`gui/walk.py`), so a lenient fold has to exist below `gui` before the stack can
read one. And a stage *name* — "spatial prep", "signal extraction" — is derivable
from nothing at all; whether the header carries only the chip, or the vocabulary
of stage names is minted as a declaration, is the ruling this item wants and not
a thing a work run picks on the way past.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k stage_header
    132 deselected in 0.68s
    exit: 5

## 2026-08-09 (review): the module that defers to this item cites a slug that does not exist

`gui/chain_stack.py`'s docstring closes by pointing here —
`todo/a-stage-header-groups-by-nothing-the-tree-declares.md` — and that file
has never existed; the item is `...groups-cards-by-nothing...`. The reader the
docstring was written for lands nowhere, which is the whole of what the
sentence was for. Correct it in the commit that answers this item, since that
commit is already in both files.

Nothing in the tree checks a reference like this. `doc_index.py` reads
frontmatter and `tests/docs/test_doc_index.py` asserts ordering; neither
resolves a `docs/`-relative link out of a source docstring, so a misspelled
one is silent. A crude scan over `src/**/*.py` and `docs/**/*.md` at this
commit turns up on the order of thirty candidates, most of them v2-relative
paths into a tree this repo does not hold and one of them a deliberately
misspelled example inside
[what-earns-a-place-on-the-gate-line.md](what-earns-a-place-on-the-gate-line.md).
Whether a checker is worth its false-positive rate is not this item's call and
is not minted as one; what is recorded here is that the class exists and goes
red nowhere.
