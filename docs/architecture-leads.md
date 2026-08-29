# Architecture leads

Ideas judged worth holding, each waiting on the evidence or the trigger that
would mint it. Nothing here is settled — settled lives in `docs/adr/`. An
entry graduates the usual way, through a measurement or a wound in this tree,
and leaves this file when it does, in either direction.

## Data carries its coordinate frame

A position at (x, y) means nothing without knowing which pixel grid x and y
are in. Crop, downsample, letterboxing, and undistortion each change the
grid, and a coordinate that crosses such a boundary without its transform is
the spatial twin of the wound ADR-0004 closed: two modules each correct, one
silent convention between them, results wrong with nothing red. The lead:
a position carried on an edge or written into a durable record names its
grid — raw source pixels unless stated — and anything that changes the grid
carries the way back.

Trigger: the first geometric transform whose output is consumed — an overlay
mapping display coordinates back through the canvas's centring and
letterboxing to source pixels, or the first crop a tool reads. Mint from
that concrete case.

## A parameter declares whether it can reach the value

A step's parameters divide: those the recorded value depends on, and those
that only change how it is drawn. ADR-0005 and ADR-0010 fold the first kind
into the durable key; the lead is to make the second kind a declared class,
so turning a cosmetic knob provably invalidates nothing — the loop redraws
without re-keying, and a cache is never dropped for a change that could not
have reached it. The boundary earns its own argument when a real knob sits
on it: a parameter declared cosmetic that feeds anything recorded is a
mis-declaration with exactly the silent-staleness failure ADR-0010 exists
to prevent.

Trigger: the first step carrying both kinds of knob.

## The tool contract as a runnable suite

ADR-0009's second prohibition — a tool never reaches past the contract — is
only as strong as its enforcement, and the tools are written by agents. The
lead, in scikit-learn's `check_estimator` shape: the contract's clauses
(declaration honoured, coverage recorded, key complete) as one suite any
tool is run against, so a tool is trusted because it passed, not because its
author was careful. Tooling under ADR-0009 in the `checks/` style, not a new
decision.

Trigger: the contract growing clauses — when the composition questions
ADR-0009 deferred start settling.

## The decoder is an input

Decoder builds are not bit-stable against each other, so a decoded frame's
bytes depend on which decoder produced them. Under ADR-0010's rule that is
a third-party solver: named and versioned in `params` of whatever key
covers decoded output, never ambient.

Trigger: the first durable key over decoded pixels.

## A persistent format is versioned from its first byte

When a format meant to outlive a session is minted — a manifest, a pipeline
file, the store's key scheme — a schema version goes in before the first
real byte does. The cost is one field now; the retrofit is orphaning every
artifact in existence, silently. Not a standalone ADR — one clause in
whatever ADR mints the artifact.

## Correctness as relations, not examples

Most of what SIEVE computes has no oracle — nothing says what a flow field
should be — so a test written by running the code can only encode what the
code did. v3 is the measurement: its `tests/` outgrew its `src/` in lines,
example-based throughout, and none of it survived into this tree. The lead
is correctness stated as implementation-free relations instead: invariants
over generated inputs, and relations between runs where neither output is
checkable alone — a step downstream of a crop agrees with cropping its
output; decimation moves timestamps exactly as declared and nothing else.
Relations restate the contracts, which is why they survive the rewrites
examples don't — and they are authored by whoever owns the contract, never
by the agent that wrote the code under test, or they encode the
implementation again with extra steps. Golden masters keep one small
curated job: catching unintended change, a human blessing the diff.

Trigger: the first contract worth holding — likely the declaration and
coverage clauses of ADR-0005/0006.

## Sweeps stay outside

A parameter sweep or a replicate set is many runs, not a bigger run.
Whatever generates them owes SIEVE nothing, and SIEVE owes it only run
records a machine can read and instantiation such that variants share their
cached prefix. Keeping that layer outside is ADR-0009 applied to
experiments; the alternative is the framework that grows a loop over
videos, then a configuration matrix, then plotting, until the core cannot
change without breaking someone's figure script.
