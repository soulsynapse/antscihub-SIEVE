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

## A document has one writer

Two writers on one file is where a durable format goes wrong, and it is not
the same question as whether the file is committed: `Cargo.lock` is
machine-written, checked in, and quiet, because cargo is its only author.
What breaks is the file a person edits by hand and a program also rewrites —
the rewrite reformats what they wrote, the hand edit is a conflict the
program cannot merge, and the file stops being readable as a statement of
intent because half of it is a report. The lead: a durable document names
its writer, and a fact with a different writer goes in a different document
rather than a different section of the same one. What a project is *for* is
authored; what a run resolved, produced or cached is reported; the two ship
together and are still two files.

Trigger: the first document with a plausible second writer — a project or
pipeline file the application would also like to update as it runs.

## Portable and machine-local are different documents

Whether a fact travels is a second axis, orthogonal to who writes it, and
the two together give four kinds of document rather than two: authored and
portable (intent), authored and local (this machine's scratch path, its
queue account), reported and portable (what a run resolved), reported and
local (what a probe measured here, which projects this person has opened). A
scratch path or a machine-dependent measurement written into a document
meant to travel is wrong on the machine that receives it with nothing red —
the durable-instruction failure, in a file instead of a comment. The lead: a
durable document says which of the four it is, and the split is by file, the
way DVC separates `config` from `config.local` and git separates a repo's
config from the user's, rather than by a section a reader has to remember
not to trust.

The corollary is on paths. A document that travels names its neighbours
relative to itself, because its own location is the only fixed point it has;
one that never leaves this machine names them absolutely, because finding
them here is its whole job. Neither rule survives being applied to the other
kind of file.

Two of the four are already placed, and each states its own terms where it
lives: ADR-0007 holds that a cost class is measured where it runs, so it was
never portable, and `src/sieve/project/library.py` is a per-user document
held out of every project.

Trigger: the first document a second machine reads — the pipeline's
persistent form, per the lead below.

## The pipeline document is the cluster handoff

HPC batch is an aspiration, and it constrains the present: a pipeline's
persistent form must be findable and executable by a process with no GUI
attached, because a cluster job is exactly that process. One document, two
consumers — the GUI edits what the headless runner executes — or the GUI's
private reading becomes the only complete definition and the aspiration is
foreclosed without anyone deciding to. v3 already held this shape; its
pyproject names the saved project "the cluster handoff" and reasons about
headless installs.

Trigger: minted with the pipeline's persistent format — whose first-class
reader is the headless runner, the GUI a client of the same reading.

## A pipeline is not a property of a recording

The recording, the analysis run on it, and the values that apply one to the
other are separate documents: a project document beside the recording, a
pipeline document the user owns and keeps wherever they keep their work, a
parameter document holding values a port can be satisfied from, and a take
naming one pipeline, the version it bound against, and where each port got
its value. None contains another, and the references run one way — a take
names a pipeline and a parameter document, and neither ever names a recording.

The argument is revision, not tidiness. A pipeline is corrected *after* the
recordings it was applied to have been analysed — tune a chain on one, apply
it to forty, then find the mistake in step three — and under embedding that
fix is forty edits with nothing able to say which of the forty are now
corrected. The null option is the bundle: ilastik's `.ilp` carries workflow,
labels and cached features together, and applying somebody else's classifier
to your data becomes an awkward operation on a file that is mostly their
pixels. CellProfiler splits it the same way, and the artifact people cite in
a methods section is `.cppipe`, the definition — which is the tell for which
half carries the science. The opposite error is DeepLabCut's `config.yaml`
holding an absolute `project_path`: a machine-local fact written into the
document meant to travel. So requirement in the document that travels,
resolution in the one that does not.

Values live apart from both because a port's value may be proposed by an
optimiser, generated by a sweep, or computed by a script, and a value held
inside a document SIEVE also authors makes every such generator rewrite that
document. A port therefore names a document and a key within it, since one
crop document holds several named regions — which is what `Edge.name` in
`sieve/contract/edges.py` is already doing on the source side.

Trigger: minted with the pipeline's persistent format, alongside the leads
above and below it.

## A recording's identity is a fingerprint its source produces

A path is where a recording is, not what it is, so anything durable beside one
needs an identity that survives a rename. The source owns producing it,
because only the source knows what its address is made of, and the field names
its algorithm rather than implying one — `tools/video_file_source.py` spells a
sparse byte fingerprint, and a content-level one has to be able to coexist
with it rather than orphan what was written under it. A source with no durable
identity at all, a camera, returns none.

Byte identity rather than content identity, and the direction it errs is
deliberate: a lossless remux fingerprints differently, so SIEVE calls it a
different recording where a person would not. A false alarm asks a question;
the alternative silently accepts the wrong file. Hashing decoded pixels is
refused on cost, not availability — a source tool has a decoder, but it means
decoding the whole file. Repair of a rename is offered and never performed:
`video.mp4` beside `video_backup.mp4` is an ordinary folder, and byte-identical
copies make the match genuinely ambiguous in a way only the user settles.

Trigger: the first thing written beside a recording — which is also when
`.sieve/<stem>` and the rule that nothing appears there until there is
authored content to write have to be settled. Lab footage sits on read-only
archives, and a tool that writes into somebody's data directory because they
looked at a file is one they learn to work around.

## A pipeline carries a UUID, a name and a version

Three jobs, not one. The UUID survives a rename and a move, which is what a
reference needs and what a path cannot give — the location-versus-identity
distinction `src/sieve/project/library.py` already records about its own key.
The name is what a human picks out of a list. The version is what makes "v2
dropped a parameter" sayable, so a take that recorded what it bound against is
checkable when it is opened rather than discovered wrong on a cluster node an
hour into a queue. Content hashing is refused for the reason
[ADR-0010](adr/ADR-0010-a-key-carries-a-version.md) refuses it in a key: every
edit would mint a new identity, and *the same pipeline, corrected* is exactly
what must stay expressible.

Trigger: as above.

## Correctness as relations, not examples

Most of what SIEVE computes has no oracle — nothing says what a flow field
should be — so a test written by running the code can only encode what the
code did. v3 is the measurement
(`docs/findings/2026.08.28-the-v3-suite-outweighed-its-program.md`): a
suite larger than its program, example-based throughout, of which nothing
survived into this tree. The lead
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

## A parameter is a port

A threshold gated on an upstream computation and a step consuming a previous
step's output are the same edge; what differs is that one is tied to a frame
and a time and the other is not. That makes position-indexing a property of
the edge rather than a category of thing on either end, and the parameter/input
distinction thinner than it looks — a constant is a value whose declaration
ignores position, which is ADR-0006's declaration in its degenerate case rather
than a second mechanism beside it. The lead: parameters are ports on that one
graph, and a port nothing satisfies is a pipeline that refuses to run rather
than one that runs on a default.

What stays a real distinction is not parameter-versus-input but provenance —
when the value is known and who supplies it. Authored before the run, produced
during it, or read from a document, which is the mode the lead above mints
parameter documents for: a value an optimiser or a script produced has to be
addressable, or its generator ends up rewriting a document SIEVE also authors.
A port declares what it needs and never where to get it — naming a location
inside the document that travels is the failure recorded there against
DeepLabCut's `project_path`.

Trigger: minted with the pipeline's persistent format, alongside the lead
below and the two above it — they constrain each other and want deciding
together.

## A fan-out names its axis

A crop that is four replicate boxes fans the graph out to four branches, and
the same is wanted for a threshold varied deliberately or proposed by an
optimiser. Where it gets decided is two ports fanning out at once: three crops
and four thresholds is twelve branches or an error, and every system that has
faced this makes the author say which — Nextflow separates `combine` from
`join`, Snakemake's `expand` is cartesian unless passed `zip`, GNU parallel
spells the difference `:::` against `:::+`. The lead is that the choice is
offered at the join, and that the axis carries a name with labelled
coordinates, because the names buy what the choice does not: replicate 3 in one
recording is the same replicate in another, so pooling aligns by name rather
than by the order somebody's hand moved when they drew the boxes. Each branch
keys independently, which is ADR-0005 and ADR-0010 already — a coordinate is
something consumed — and that is what lets a fifth box re-run one branch and
reuse four, which is the interactive loop surviving the edit it will see most.

Trigger: as above.
