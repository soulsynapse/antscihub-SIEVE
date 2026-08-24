# substrate-checks

Where `src/sieve/` is checked, one file per phase of
`docs/substrate/port-plan.md`.

Not a second kind of experiment and not a test suite. This tree already has a
notion of evidence — a script that attaches its build, machine and probed
footage, keeps every sample it took, discards a stated warm-up, and commits its
JSON, where a silently absent case reads as a case that came out equal. A
second mechanism beside that would give the tree two disagreeing answers to
what counts as proof, so these import `../decode-experiments/harness.py` like
everything else and repoint `harness.RESULTS` here.

What differs is what they are asking. The other folders ask *how expensive*.
These ask *whether an invariant holds*, which is the shape
`tool-experiments/05-provenance.py` established: a sentence-long property, a
handful of cases in increasing nastiness, and a deliberately broken mode
(`--broken`) run alongside — because a check that has never failed has no
demonstrated power.

Cost is not absent from them, it is just not the point. Where a check happens
to time something worth keeping — what a table costs to build, what a cache
saves — it records it as a case and the numbers live in `results/` with
everything else.

A check that needs no footage says so by attaching none. Several of the
properties here are about arithmetic and hold on a table that was never read
off a file, which is deliberate: those are the ones that stay checkable on a
machine with no `video-tests/`.

## Running

    uv run --group experiments python experiments/substrate-checks/<name>.py
    uv run --group experiments python experiments/substrate-checks/<name>.py --broken

Footage comes from `video-tests/`, gitignored. A check that cannot find what it
needs says so in its notes and carries on with the cases it can run.
