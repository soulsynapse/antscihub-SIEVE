---
title: The overview and its estimate lost the screen they were to arrive on
phase: 9
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_save_and_run.py -q -k 'the_run_row_states_what_it_will_do or an_estimate_is_measured_not_declared'"
opened: 2026-08-09
---

# The overview and its estimate lost the screen they were to arrive on

Three places defer to one surface that no longer exists. `gui/save_screen.py`
closes its docstring with "what stays unbuilt: the overview and the time estimate
VISION puts on this screen, which is the consumer that revives the spec's cost
declarations and arrives with it". `core/tool_base.py` cut `CostEstimate` on the
same reasoning, and
[the-plan-is-rederived.md](the-plan-is-rederived.md) dropped a ported case citing
it. Then `MOCKUP-MAP.md` dissolved the screen: Run sits on the output card's
form, and there is no process screen for the overview to arrive on. The
declaration's consumer is now homeless, which under
[adr/declared-means-verified.md](../adr/declared-means-verified.md) is the state
that decides whether the declaration comes back at all.

VISION's sentence still stands and is worth keeping: selecting process "gives
them an overview of the steps and an estimate of the time it'll take on this
machine". Both halves are cheap on the output card's form — the overview is the
walk the card is already drawn over, and the estimate is one line under Run.

The fork is what the estimate is made of, and it should not be settled by
whoever writes the widget. Declared `ToolSpec` cost fields are what VISION names
and what Phase 1 cut pending this consumer. Against them: the estimate can be
extrapolated from the sample the user already ran — the preview session has run
the chain, `bench/metrics.py` has the timings, and no spec field is needed at
all — and `declared-means-verified` should prefer the reading that adds no
declaration. The local evidence is on that side too: v2's own audit found
declared constants drifting silently out of agreement with the code they
described. The second `-k` term names the measured reading because it is the one
this item argues for; a session that takes the declared reading changes the name
and says why.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui/test_save_and_run.py -q -k 'the_run_row_states_what_it_will_do or an_estimate_is_measured_not_declared'
    4 deselected in 0.13s
    exit: 5
