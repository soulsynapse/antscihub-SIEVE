"""The terminal front end: the run path that has no toolkit to hide behind.

BOUNDARY: Typer stays in this package, exactly as Qt stays in `sieve.gui`.
Nothing below imports a command, and nothing here is imported by the GUI —
the two are siblings at the top of the layer stack, and a shared helper that
drifted into one of them would be a second place a run is described.

`SCAFFOLD.md` calls this "the canonical run path — built and tested before
GUI", and the ordering it asks for cannot be honoured literally by a repo
whose GUI already exists. What *can* be honoured is the reason behind it: the
executor is meant to be the single execution path, and a GUI is a poor witness
to that because it can reach a frame through a decode thread, a coalescer, and
a display proxy without `pipeline/executor.py` being involved at all. A CLI
has none of those. If `sieve run` produces frames, the shared path produced
them, and `tests/integration/test_cli_run.py` is what says so.

**These commands own no arithmetic.** Ordering is `Dag.order`, lead-in is
`ExecutionPlan.lead_in`, keys are `dag.node_keys`, and the loop is `execute`.
What is left for a command is argument parsing, one decision the document
cannot make (which span, which replicate, which backend), and printing. A
command that computed anything about a run would be the second answer this
package exists to prove does not exist.
"""
