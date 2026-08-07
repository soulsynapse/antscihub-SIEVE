---
title: A filter declares the extents it emits
status: open
opened: 2026-08-06T17:56:51-07:00
priority: normal
gated_on: nothing structurally
reads:
  - src/sieve/pipeline/lowering.py
  - src/sieve/core/filter_base.py
  - src/sieve/filters/downsample.py
serves: [A2]
---

`pipeline/lowering.py` enumerates filters and reimplements their output
geometry, and rule 3 as sharpened on 2026-08-06 fires on it: adding a shrinking
filter now requires editing that file. It hardcodes `crop`, `downsample`, and
`rescale` by id with a literal version pin (`_is`, line 128), and then computes
each one's output extents itself — `crop.width // factor` at line 152 and
`max(1, round(crop.width * scale))` at line 175. Those match
`filters/downsample.py:107` and `filters/rescale.py:101` today, exactly, and
nothing holds them together: no shared derivation, no test comparing lowered
geometry against what the removed nodes would have produced. A rounding change
in either kernel silently desynchronises the FFmpeg prefix from the graph it
replaced, and the symptom is pixels that are one row different with a cache key
that says they are the same.

It does this because there is no way from outside a filter to ask what extents
it emits for a given input. `FilterSpec` declares `accepts`, `emits`, `element`,
and `cost`; `ParamsBase` declares `output_rate`, `warmup_frames`,
`max_warmup_frames`, and `frame_bytes_ratio`. None is a shape function, and the
nearest one is explicitly not: `frame_bytes_ratio` is a *ratio*, documented as
approximate ("off by less than a row and a column", `downsample.py:87`) because
it feeds a storage prediction and never a correctness decision. `crop.py:94`
states the structural reason a ratio cannot be promoted — "the fraction a crop
keeps is `roi.area` over the input frame's area, and the second term is not a
parameter." A ratio takes no input; extents do.

## What to build

**Where it lives: `ParamsBase`, not `FilterSpec`.** The geometry is a function
of `factor`, `scale`, and `roi`, which are parameters, so it belongs beside
`output_rate` and `frame_bytes_ratio` and not beside `emits`. This is the whole
placement decision and it is the reason the item exists rather than being a
cleanup: `FilterSpec` is class-level and could never answer for a configured
node. `output_rate` is the precedent to copy in every respect — an override
detected by identity against the base method, a default that is the identity
answer, and a spec-level flag only where an undeclared override would be silent.

**What it takes and returns.** Input extents in, output extents out:

```python
def output_extents(self, incoming: Extents) -> Extents | None: ...
```

`Extents` is a two-field frozen dataclass (`width`, `height`) in
`core/types.py`, not a bare tuple — the tree already pays for `ROI`,
`FrameCount`, and `FrameIndex` being nominal and a `(w, h)`/`(h, w)` swap is
exactly the confusion those types exist to refuse. The default returns
`incoming` unchanged, which is the honest answer for every filter that
preserves shape and is most of the shelf.

**How a filter says it cannot answer.** `None`, and it must be `None` rather
than a raise or an optimistic guess. Two filters need it today for two different
reasons, and the item is not done until both read correctly:

- `block_signal` emits an `(ny, nx)` block grid, which *is* a pure function of
  the input extents (`grid_shape`) — so it answers, and answering is what stops
  a future consumer assuming the frame passed through unchanged.
- A filter whose output shape depends on pixel *values* rather than extents —
  none on the shelf, and `detect`'s `(1, 1)` is the near miss — returns `None`.
  A consumer that gets `None` must degrade to not-lowering, not to guessing;
  `lowering` already has that branch and it is the one it returns from.

The declaration must be *checked*, not trusted, or it becomes the third copy
instead of the one home. The check is a property test over the discovered shelf:
for every filter with a CPU kernel, run one synthetic frame through the kernel
and assert the produced frame's extents equal `output_extents` of the input's —
the shape `tests/property/test_filter_settling.py` uses for warmup, and for its
reason. A filter answering `None` is exempt and enters a shrink-only list, so
the exemption is visible rather than silent.

**How `lowering.py` consumes it.** `_scale` stops asking *which filter this is*
and starts asking *what does this node do to these extents*. It resolves the
node's params (it already does, three times, at lines 87, 144, and 165), calls
`output_extents(crop_extents)`, and keeps the node as a lowering candidate when
the answer is strictly smaller on both axes and is not `None`. `_is`'s hardcoded
ids and the `"1.0.0"` version pin go with it, and so does about forty lines.

## Two constraints from the audit that this must not lose

**The version pin at `lowering.py:128` currently disables lowering silently.**
`_is` matches `node.version == "1.0.0"`, so bumping `downsample` to `1.1.0`
makes every lowering attempt return `None` — no diagnostic, no log line, no
change on screen except the cold fill going back from 1.6 s to 6.9 s
(`docs/findings/2026.08.06-working-frame-before-python-buys-the-cold-fill.md`).
Deleting the pin removes the failure, but the item should not remove it by
accident: replacing it with a shape declaration is correct precisely because a
filter that changed its geometry declares the new geometry, which is the thing
the pin was standing in for. Say that in the completed entry, because otherwise
the next reader restores a pin.

**The three `cast(Any, ...)` at lines 87, 144, and 165 are the same problem seen
by the type checker.** They exist because `dag.spec(...).params_model` is
`type[ParamsBase]`, so `params.factor` and `params.roi` are unknown to pyright
and the cast is how the file reaches a field the outside has no typed way to
ask for. A shape declaration that still needs a cast has not solved this: the
point of putting `output_extents` on `ParamsBase` is that it is a *declared
method on the base class*, callable through the base type, so the resolved
params never have to be narrowed to a subclass at all. If the implementation
ends with `cast(Any, params).output_extents(...)`, it is the wrong
implementation. Zero casts in `lowering.py` is the observable end state, and it
is a better completion check than the line count.

## What done looks like

`lowering.py` names no filter id and no version. `grep -c "cast(" 
src/sieve/pipeline/lowering.py` is 0. A new shrinking filter is lowered by
declaring `output_extents` and editing nothing outside its own module, which is
rule 3 stated as an observable. The property test fails if any filter's declared
extents disagree with what its kernel produces.
