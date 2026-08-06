"""Array math as a declared kind: arrays in, arrays out, no state and no spec.

An op is not a filter. A filter is a `FilterSpec` plus a registered kernel, is
discovered automatically, and fills a step of a pipeline; an op is a function
the caller has to know the name of. Nothing here registers, and nothing here
holds a frame's worth of state between calls.

This package makes no reuse claim, and that is deliberate. The two duplicated
primitives in the tree today — the `ChannelSpec` to `cvtColor` code branch, and
the `INTER_AREA` resize — are both OpenCV calls, so `core-purity` forbids them
here and they stay beside their kernels in `sieve.filters`.

**What it buys is a position no other package can hold**, which is a stronger
claim than the tidiness this docstring used to make and is the one to answer if
you are wondering whether the directory earns itself. `filters/` imports this
math, so it must sit below `sieve.filters`. It cannot sit *in* `filters/`:
discovery globs `*.py` there and `test_every_discovered_filter_has_guidance_
markdown` pairs each module with its own `.md`, so a helper there is a filter
with no markdown. It must not sit in `sieve.detect`, which is where every
current consumer lives and is exactly the trap — that package is the schema-v5
compatibility layer three open items are dismantling
(`sieve-detect-collapses-into-sieve-run`, `detector-state-dies`,
`rule-sixs-frontier-moves-into-the-contract`), while `morlet_power` and
`detect_gate` outlive all of it because the detect *filter* needs them either
way. And `core/`'s own root is `pipeline_model.py` and `filter_base.py` — the
saved artifact's schema and the filter contract, which are declarations, where
this is arithmetic carrying measured constants. Four candidate homes, three
closed, and the survivor is this one.

Git cannot corroborate that yet and will not for a while: exactly one commit
has ever touched this package, the one that created it, so the co-change test
`CLAUDE.md` prescribes has no evidence to read. The argument above is what
stands in for it until there is some.

The reason the split is drawn here rather than at a top-level `sieve.ops` above
`core`: `core-purity` already asserts what an op in this repo is allowed to
touch — no toolkit, no codec, no processes — and a new layer would have to
re-earn that in a contract of its own. When a second filter needs the optical
flow that `filters/block_signal.py` keeps private, the reuse argument for that
layer makes itself; it does not follow from symmetry with this one.
"""
