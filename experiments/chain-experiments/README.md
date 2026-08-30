# chain-experiments

Where SIEVE finds out what happens when a step stops being the last thing in
the tree. `tool-experiments` settled what one step costs and what it leaves
behind; `orchestrator-experiments` settled how declarations schedule fetching.
This folder is the join: what a step has to say about its output before
anything can bind to it, and what a binding can work out for itself.

It exists because of a scope decision rather than a measurement.
`contract/nodes.Step` gained a producer side — `produces`, a name and a kind
and a dtype per product — on the claim that everything it *stopped short of*
is derivable from what feeds the step. A claim that convenient wants a
falsifier before a package is built on it, and a claim about derivation cannot
be tested with one step: `lk_flow` admits `(-1, 0)`, where reach, span and the
count of admitted inputs are all 1, so three different derivations all look
right.

## What it is asking

**Is a step's positioning and extent derivable, or did the step have to
declare them?** `01-derived-binding.py` binds two steps of different reach to
one source and checks the heads, the positioning, and a read back out through
the binding. It runs against `tools/synthetic_source.py`, which is the only
source that can be asked to be forward-only on demand — the case where the
derived answer and the input's answer differ, and therefore the only one where
"derived" is distinguishable from "copied".

`lag_mhi` was ported into `tools/` for this, from the three loads
`tool-experiments` measured. It is the one whose admitted set is not its
reach — four inputs spanning thirty-one — which is what makes a derivation
trimming by the wrong one of those numbers fail here and nowhere else.

**Can a step say what it wants, and be fed another step's field?**
`02-chained-field.py` is the second question and the one that reopens
`contract/edges.py`. Every chain this tree can build is a fan one deep,
because `pipeline/binding.py` hardcodes a FRAME upstream and a step's
products are values. `02` makes the want a record, adds FIELD to the kinds,
binds `lk flow`'s field to a step that consumes it at lags 30/20/10, and
prices serving that field held against recomputed.

## What it has found

Numbers and verdicts live in `results/`, where a later run supersedes an
earlier one by sitting beside it. Two things worth reading before the next
person re-derives them:

**A head is a pts, not a row.** The first version of check 1 asserted that two
steps' extents start `reach` apart, which is true in rows and wrong by a
factor of the tick rate in the coordinate the contract uses — the heads came
out 29029 apart, not 29. ADR-0004 says this and the code still went the other
way on the first try. Nothing would have flagged it: both numbers are
plausible, and one of them is a position that exists.

**A value edge's payload arrives in `Answer.frame`.** `Answer` was written
when the only producer was a source, so a float now travels under a field
named for pixels. `__post_init__` only tests `is None`, so `0.0` is safe — it
is the name that lies, and renaming it to `payload` is cheaper than forking
the record.

**A field's form is a frame's form wearing a different sample format.**
`nodes.Step` refuses to offer the field on the ground that image-sized
float32 would grade EXACT against a uint8 gray frame over the same rect.
Spelling the sample format in `Form.pix` closes that inside `grade`, which is
where the mistake would be made, and separates the two `Form.key()`s a
durable key is folded from — and `_FROM` gains no entry, because a
measurement resampled is a different measurement rather than a coarser view
of the same one. A field want is matched by form equality.

**Reach composes and the naive trim is one row wrong.** Over `lk flow`
(reach 1) a consumer of reach 30 has no honest answer before row 31. Trimming
by the consumer's own reach alone puts the head one row early, computed from
an upstream field whose inputs do not exist — at the head of every chained
series, with nothing red.

**Holding a field is worth roughly what its reuse says, less the consumer's
own arithmetic.** A consumer at those lags asks for each upstream field
3.56x over a 240-row sweep, and holding them under ADR-0006's release rule
costs `reach + 1` fields. What that buys, and what it costs at full
resolution, is in `results/` — read the newest, not this line.

**`Produced.name` is tool-local.** Two crops of one step both offer `"flow"`.
That is not a defect and it is not the step's to fix; qualifying a name across
a chain is the pipeline's job, and knowing it now is much cheaper than
discovering it once the name is in the tool contract.

## The substrate

`bind.py` — the derivation under test, and the code the pipeline package
ports: where each field of `Positioning` and `Extent` comes from, and why
`access` is the input's least of all. It also holds the records `02` proposes for
`contract/` — `Wanted`, `Product`, `FIELD` and the `Held` cache — out here
rather than in the tree, and opens `edges.KINDS` in one line so the cost of
the proposal is visible where it is made. `01` runs through the same binder
unchanged, on a fallback that states what `nodes.Step` implies today: a step
with no declared want wants frames at its `form_for`.
