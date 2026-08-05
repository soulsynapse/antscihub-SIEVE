"""Array math as a declared kind: arrays in, arrays out, no state and no spec.

An op is not a filter. A filter is a `FilterSpec` plus a registered kernel, is
discovered automatically, and fills a step of a pipeline; an op is a function
the caller has to know the name of. Nothing here registers, and nothing here
holds a frame's worth of state between calls.

This package makes no reuse claim, and that is deliberate. The two duplicated
primitives in the tree today — the `ChannelSpec` to `cvtColor` code branch, and
the `INTER_AREA` resize — are both OpenCV calls, so `core-purity` forbids them
here and they stay beside their kernels in `sieve.filters`. What this package
buys is that `morlet_power` and `detect_gate` stop being neighbours of
`pipeline_model.py` and `filter_base.py`, which are the saved artifact's schema
and the filter contract and are not the same kind of thing at all.

The reason the split is drawn here rather than at a top-level `sieve.ops` above
`core`: `core-purity` already asserts what an op in this repo is allowed to
touch — no toolkit, no codec, no processes — and a new layer would have to
re-earn that in a contract of its own. When a second filter needs the optical
flow that `filters/block_signal.py` keeps private, the reuse argument for that
layer makes itself; it does not follow from symmetry with this one.
"""
