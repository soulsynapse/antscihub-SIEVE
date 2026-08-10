---
title: The declaration harness picks its feeder alphabetically and calls it the quietest tool on the shelf
priority: normal
phase: 2
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_declarations_run.py -q -k the_feeder_a_merging_case_stands_on_alters_no_frame"
opened: 2026-08-10
---

# The declaration harness picks its feeder alphabetically

11.3 gave `tests/unit/test_declarations_run.py` a way to run a tool with named
ports, which cannot be a root: `upstream_of` finds one node to stand above it.
Its docstring says which node that is — "the shelf's own answer to *what changes
least about a frame it is handed*, by id so that two equally quiet tools do not
make this depend on scan order". The code does not compute quietness. It tests
four structural properties — not a source, a `SOLE_PORT` input, `STREAMING`,
not stateful, no warmup, `emits` admitted by every port — and returns the first
qualifying spec in `tool_id` order. Sorting by id is not a tie-break among
equally quiet candidates; it is the whole rule.

Measured on the tree at 79adec6: five specs qualify — `crop`, `downsample`,
`normalize`, `rescale`, `span` — and `crop` wins on the letter `c`. Two of the
other four are not quiet in the sense the docstring claims. `span` selects and
`downsample` changes the rate, and these cases read `list(execute(plan, ...))`
as well as the recorded widths, so a feeder that drops or resamples frames moves
what every merging case observes about the tool under test. Nothing in
`upstream_of` excludes either; today's answer is correct by alphabet.

What should be different: the property the harness needs is asserted where the
feeder is chosen, so the choice cannot quietly stop having it. A tool added
tomorrow whose id sorts before `crop` becomes the feeder for every merging case
on the shelf, and the failure that follows is a merging tool's declaration
certified against frames its feeder had already altered — which reads as the
tool's own behaviour and is not. `rate_changing` and `selecting` are declared,
so the predicate can simply say so; the case in `done_when` is the assertion that it
does, over whatever `upstream_of` returns rather than over the name `crop`.

Either the docstring stops claiming a ranking or the code starts computing one.
The first is cheaper and the second is what the sentence promised a reader;
whichever lands, `CLAUDE.md`'s rule that a comment a reader cannot derive from
the code must be true of the code is what is broken today.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/unit/test_declarations_run.py -q -k the_feeder_a_merging_case_stands_on_alters_no_frame
    45 deselected in 0.60s
    exit: 5
