---
title: The first multi-input tool lands, and VISION's lead scenario stops being refused
step: "11.3"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_subtract.py -q -k 'two_inputs_arrive_on_named_ports or a_crossed_pair_is_not_the_same_graph'"
opened: 2026-08-09
---

# The first multi-input tool lands

This item is the one
[a-merge-keys-its-inputs-by-port.md](a-merge-keys-its-inputs-by-port.md) has
been deferred on since 2026-08-07. Its 2026-08-09 ruling says the gate is prose,
invisible to the index's named-gate scan, and that "the item that mints the first
multi-input tool must cite this one in its body — that citation is the whole
net". This is that citation. Whoever lands this reads that item first and moves
it out of `deferred` in the same commit, or the net was decoration.

The scenario is VISION's lead one, and today it is structurally refused rather
than merely unbuilt: `Pipeline` raises "two edges feed X", `accepts` names one
stream, `ToolRun` takes one window. 11.2 is what retires all three; what is left
here is the tool that stands on them — a subtraction taking a plate on one port
and a background on the other, which is the shape
[the-outputs-reach-down-behind-the-cards.md](the-outputs-reach-down-behind-the-cards.md)
already draws the edges for and
[the-output-card-is-a-picture-of-the-write-list.md](../adr/the-output-card-is-a-picture-of-the-write-list.md)
already ruled the output card will never be an instance of.

Two things it must not quietly become. It is not the place the semantic axis gets
decided — which of its two inputs is "the background" is
[which-axis-carries-a-meaning-like-generated-background.md](which-axis-carries-a-meaning-like-generated-background.md),
and a tool that answers it by naming a port has smuggled a scene description into
a signature. And it is one file in `sieve.tools` with zero edits elsewhere
([adr/a-tool-is-one-file.md](../adr/a-tool-is-one-file.md)) — if the tool needs a
helper module, the extension in 11.2 was not finished and this step stops rather
than papers over it.

The second `-k` term is the crossed pair, which is where
[the-discover-ordering-claim-needs-a-second-tool.md](the-discover-ordering-claim-needs-a-second-tool.md)'s
problem recurs in a harder form: a graph and its port-swapped twin must not be
the same graph, and until now no graph in this repo has had a twin.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/unit/test_subtract.py -q -k 'two_inputs_arrive_on_named_ports or a_crossed_pair_is_not_the_same_graph'
    ERROR: file or directory not found: tests/unit/test_subtract.py
    exit: 4
