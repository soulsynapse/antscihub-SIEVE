---
title: The save screen checks off outputs, and the run button issues the CLI command
step: "07.9"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui/test_save_and_run.py -q -k 'the_checkoff_writes_the_projects_lists or the_run_button_issues_the_cli_command'"
opened: 2026-08-08
---

# The save screen checks off outputs, and the run button issues the CLI command

The save screen lists *all the possible* outputs the tools could emit, read
from the specs so the list cannot lie (VISION.md;
`a-tool-declares-what-it-can-emit.md` is the declaration it reads). Checking
one off enters as SetOutputs and writes `Project.checkpoints` and
`Project.outputs` — and moves no cache key, which is Phase 2's reason those
fields live on `Project` and the claim the intent test already pins.

Run is the saved file handed to `sieve run`: the GUI issues the same command a
cluster node would, because `gui` and `cli` are peers the layers contract
keeps apart and because executing the identical artifact headless is the HPC
handoff VISION promises — this button is the first thing in the product that
exercises it. What stays unbuilt: the time estimate and the cost declarations
it would revive wait for that screen (`adr/declared-means-verified.md` — the
estimate is the consumer, and this cut does not build it), and a run that
fails mid-footage fails in the CLI's words, surfaced, not swallowed.
