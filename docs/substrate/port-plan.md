# Substrate port — the plan in phases

Not a finding and not an ADR. This is the route from the experiment folders
to `src/sieve/`, kept only while it is being walked: a phase leaves this
file when its code lands, and the file leaves the tree when the last one
does. Numbers are cited to the finding that holds them and never restated
here, because a plan that quotes a measurement is wrong the moment the
measurement is retaken.

The experiment folders stay where they are. They are the reference
implementation and the record of what was tried, including what was ruled
out, and nothing is deleted from them to mark a phase done.

## What is actually being built

Not a port of the explorers. The explorers are two driven prototypes, and
what they were driven *to* is the point — but they are not the strongest
version of what they found, and in one important respect they are the older
version of it.

Three modules in `experiments/tool-experiments/` — `forms.py`, `tools.py`,
`series.py`, with `surfaces.py` beside them — were written after the
storage explorer and supersede parts of it. They import no Qt, hold no
mutable module state, take everything as parameters, and were built against
ADRs 0004–0007 directly. They are not prototypes that need porting; they
are the design, and their move into `src/sieve/` is mostly imports and
tests.

So the shape of the work is: **carry the tool folder's vocabulary across
intact, and rebuild the decode and storage tiers on top of it** — which is
a stronger arrangement than either explorer ran, and in several places a
smaller one, because the vocabulary deletes machinery the explorers needed
in its absence.

## The one rule the split is for

The explorers earned their numbers by being one file each. That is also why
they cannot be debugged: `_serve` is a method on a `QMainWindow` that reads
checkbox state to decide a tier, `_crop` reads a mutable module global from
three threads, and the fill order — the difference between a frozen landing
and a seamless one, per
`docs/findings/2026.08.22-what-froze-the-felt-loop.md` — is four lines
inside a thread body with no way to observe it that does not involve
decoding video.

Every phase below names a seam, and a seam is judged by one question:
**what can be tested behind it without footage, without a GPU, and without
a GUI.** Where the answer is "nothing", the split is wrong.

Three seams carry most of that weight:

- **A form is the key, everywhere.** `forms.Form` already says which source
  pixels at what sampling in what format, fixes the canonical construction
  so two producers of one form cannot disagree in the low bits, and grades
  whether something on hand may *answer* a request (`EXACT`, admissible) or
  only *show* for it (`APPROX`, never recorded). Every store below is keyed
  by `(row, form.key())`, and that single decision removes more explorer
  machinery than anything else in this plan.
- **A route is an interface, not a class hierarchy.** Serve the frame at a
  row, serve the keyframe at or before a row, say where it is parked. Three
  methods. A fake route returning synthetic arrays makes fill order, tier
  choice and eviction assertable with no video file in the repository.
- **Choosing a tier is a pure function; using one is not.** The ladder
  takes a request, the active declarations and a coverage snapshot, and
  returns a named decision. It decodes nothing, touches no disk, holds no
  lock — so the rules that cost a day of instrumentation to find become a
  table of cases instead of comments inside a widget.

## What the vocabulary deletes

Each of these is explorer machinery that exists only because the explorer
had no `Form`. Naming them is the point of the phase list below; they are
work *not* to do.

**A store that can hold two forms at once.** The session explorer is keyed
by bare row over a global `CROP_RECT`, so a display frame and a crop frame
cannot coexist and the hunt tier re-decodes a proxy segment on every
request. Keyed by `(row, form)` they coexist, which is what the decode
explorer's byte-budget cache over display frames had and what did not
survive the move to `session-explorer.py`.

**Not** the wipe, which stays. It is tempting to say form-keying deletes
it — a new crop is simply a new form, missing rather than invalidating —
and `02-form-derivation.py` measured the opposite. Derivation pays only
where decode is expensive, which is exactly where the dominating form is
too heavy to hold much of, so **the domination test belongs to the hunt
tier and the window tier keeps the wipe it already has**. That is a result,
not a preference, and this plan does not relitigate it.

**The display-tier special case.** `_serve` hard-codes that the proxy route
never feeds the crop store and that a display frame may only be shown. That
is `forms.grade` returning `APPROX`, which is a general law with a stated
reason rather than a rule about one route. Symmetrically, the keyframe
route's "free admission" — the crop sliced out of a full decode, admitted
because bytes that already exist are never refused — is `grade` returning
`EXACT` from a native-sampling form containing the wanted rect. One
mechanism, both cases.

**No display cache at all.** Because the explorer could not key two forms,
every hunt request re-seeks and re-decodes a proxy segment. The decode
explorer had a byte-budget LRU over display frames and it did not come
across. Form-keyed, one store holds both and the omission cannot recur.

**Four copies of seek-and-scan.** `Fetcher.exact`, `ProxyFetcher.frame`,
`SegmentProxy.fetch` and `ChunkStore.fetch` each contain the same seek,
decode-forward, and `pts + half >= target` tolerance. One implementation —
and the tolerance disappears entirely once the target pts comes from the
frame table rather than from `start + row / rate / timebase`. Seek, walk
forward, match pts exactly.

That arithmetic is wrong on this footage, and P0 measured *how*, which is
not the way ADR-0004 leads with. The rounding case the ADR names — a frame
lasting a fractional number of ticks — does not arise here: this source's
timebase and rate give a whole 1001 ticks per frame. What arises instead is
that the file was cut mid-GOP, so its leading packets carry timestamps
below the stream's stated start, and arithmetic that begins counting at
`start_time` is offset by the length of that head on every row of the file.
Twenty frames, silently, past any frame-scale tolerance. The result files
are in `experiments/substrate-checks/results/`.

**Coverage parsed out of filenames.** `int(p.stem.split("-")[1])` over a
directory glob, in two places, per call, with a trust heuristic bolted on
because a file being written is present but incomplete. `series.py` already
demonstrates the alternative for the analysis tier — an explicit coverage
array and a sidecar naming what the arrays are, precisely so a key never
has to be recovered by parsing a path. The frame tiers get the same
treatment.

## Three collisions the plan resolves

**The explorers disagree about the decode route, and a finding settles
it.** `decode-experiments` ends on a probed software/hardware seek race
under a cache over strided display frames; `session-explorer` uses plain
software PyAV at full resolution and lets the segment proxy displace the
hybrid. That is
`docs/findings/2026.08.21-decode-stack-best-combinations.md` being right
that file choice dominates route choice. The rule: **the probed hybrid
serves the uncut original; everything derived is served by the plain
software route.** The retired approaches in the decode explorer do not come
over.

**Durable identity by ordinal.** `chunk-000096.mp4`, `seg-00042.mp4`, and
the coverage sets read back out of those directories, all name frames by
position across sessions — the thing ADR-0004 refuses, and the thing
`series.py` already gets right by carrying a pts array and a timebase.
Rows stay the coordinate *inside* a store; what a stored span means is its
pts range in a recorded artifact.

**Trust heuristics around files being written.** The proxy reader trusts a
segment "once a newer one exists"; the builder tracks which file ffmpeg
holds open, and its kill path deletes a truncated victim so it cannot serve
short. The fix for anything we encode ourselves is free: write to a
temporary name and rename into place, so presence *is* completeness. For
the ffmpeg segment builder it is not free — piecewise availability during
the run is the property exp06 measured — so a publish step renames each
segment once the next appears. The heuristic survives, but it lives in one
publisher instead of being smeared across every reader.

## Decisions this plan takes

Five, recorded with their reasons so a later session argues with them
rather than re-deriving them.

**The window stores the crop, and a nudge pays a re-decode.** The
alternatives were storing the full native frame — every crop then derives
`EXACT` for nothing, at roughly sixteen times the bytes on this footage —
or storing a padded envelope so small moves derive free and large ones do
not. This agrees with `02-form-derivation.py`, which already put the
domination test in the hunt tier and left the window tier its wipe. The
envelope is the one option still open and it is *unmeasured*:
`experiments/storage-experiments/README.md` lists it as its fourth
measurement task, "how permissive the stored form must be for that to stay
rare", and the folder stops at 06. It is declined for now rather than
guessed at, so the margin is not picked by judgment and the question keeps
its own name. If the tuning loop turns out to feel the nudge, that
experiment is the answer and not a parameter to tune.

**Crop is a tool, and the vocabulary already carries it — as the form.**
Which source pixels a step is about is `Form.rect`, every step declares
`form_for(crop)`, and the rect reaches the series key through `form_key` in
`source|tool_key|form_key`. So crop is not an extra kind of thing needing
an extra mechanism: it is the parameter the form exists to name, and
`tool-explorer.py` runs it that way today. Nothing here is unbuilt.

That makes crop churn an instance of the general case rather than a special
one — the rect changes, the form key changes, every series about the old
picture keeps its rows and the new one starts empty, which is `series.py`'s
invalidation working as designed rather than machinery anyone adds.

What the port changes is only where the rect lives. In the explorers it is
a module global that every call site remembers to pass into `form()`, and
the one that forgets files a value under a key that does not describe it.
Owned and passed, that class of error stops being possible — which is
`05-provenance.py`'s invariant enforced by construction instead of by
checking.

**The ladder returns an ordered list of tiers to try, not one decision.**
A single decision needs a snapshot of what is resident, which either costs
a scan per request or goes stale between the choice and the use. The
explorer sidesteps both by attempting each tier in order, so the attempt
*is* the query. An ordered list keeps the pure function and its
table-driven test while making the race impossible.

**Retention consults residency; there are no per-form budgets.** One LRU
byte budget spanning a small display form and a large crop form would let a
window fill evict the whole scrub cache — the failure the decode explorer's
`CachedSource` docstring exists to make feelable. ADR-0006 already answers
it: what may not be evicted is `residency` over the horizon about to be
served, and everything outside that set is the store's to drop as it likes.

**ADR-0008 is settled before P3 opens.** The ledger's shape follows from
it: a plain event log and a full attribution — every interval charged to
something, with the remainder itself a reading — are different data models,
and retrofitting the second onto the first touches every call site.
Settling it also has to resolve, in the ADR's own text, whether a rate
stated relative to the source's own playback is a budget it refuses or a
report it permits. The tree's product constraint is phrased that way, and
the ADR's language as drafted reaches it.

**Verification extends the harness pattern rather than adding pytest.**
This tree already has a notion of evidence — a script under
`experiments/decode-experiments/harness.py` that attaches build, machine
and probed footage, keeps every per-iteration sample, discards a stated
warm-up, and commits its JSON, where a silently absent case reads as a case
that came out equal. A second mechanism beside it would give the tree two
disagreeing answers to what counts as proof. So each phase's "proves it" is
a harness script, and the ones that need no footage say so by attaching no
footage.

## Phases

Each names what it owns, what it may not know about, and what proves it. A
phase is done when its checks pass without the phase after it existing.

### Before P0 — settle ADR-0008

Not code. Move it out of `status: draft`, resolve the budget-versus-report
question against the product constraint in its own text, and let
`scripts/doc_index.py` pick it up so `docs/ADR.md` stops saying seven.
P3 cannot choose a data model until this reads as decided.

### P0 — identity and form — *landed*

`src/sieve/frame/table.py`, `.../shape.py`, `.../form.py`;
checked by `experiments/substrate-checks/01-identity.py`

Owns what a frame is and what a stored frame is. The frame table comes from
the demux-only pass at open: rows to pts, pts to rows, keyframe rows, the
timebase recorded once. Tick arithmetic is confined here and nothing above
handles a `Fraction`, which is ADR-0004's own accepted cost taken
deliberately. Alongside it, `forms.py` moves across essentially unchanged —
`Form`, `build`, `grade`, `derive`, `shortfall` — because its construction
order, its `EXACT`/`APPROX` fork and its durable `key()` are the design.

*Proved it:* six cases, passing, with `--broken` failing the two that can
see the difference. Rows and timestamps round-trip on the 5.3K source and
on two hand-built tables that need no file. The table reports packets, not
decodable frames, because a demux-only pass cannot know the difference
(`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`);
the leading packets that decode to nothing stay P1's to confirm, though
they are *visible* here as the twenty carrying timestamps below the stated
start. `build` from source and `derive` through an `EXACT` intermediate
produce byte-identical arrays, so a warm answer cannot differ from a cold
one.

The case worth reading is `derived`, which failed first and was right to.
It asserted what this plan had written down — that a proxy maps to its
source frame-for-frame by row — and found the two disagree by a constant
twenty while every proxy timestamp names a source instant *exactly*
through `rescale` alone. That is ADR-0004's twenty, reproduced from the
other end: the claim is about timestamps and never was about rows, and a
check written to the looser reading reproduced the exact bug the ADR
exists to prevent.

*Also in P0:* `av`, `numpy` and `cv2` become runtime dependencies and the
`pyproject.toml` comment forbidding them is rewritten. It protected a
comparison that is over and has a winner. `cv2` is not the marginal call I
previously took it for — `forms.build` and `forms.derive` are defined in
terms of specific interpolations, and reimplementing them would produce a
second answer to a question the module exists to have one answer to.

### P1 — routes — *landed*

`src/sieve/decode/route.py`, `.../pyav.py`, `.../hybrid.py`, `.../probe.py`,
`.../fake.py`; checked by `experiments/substrate-checks/02-routes.py`

One deviation from what this section first listed: software and hardware are
one class and two constructors in `pyav.py`, not two files. They differ in a
single open option, and two files would have been a copy of a seek loop —
which is the thing this phase exists to stop there being four of.

Owns getting pixels out of one file: an exact row, the keyframe at or
before a row, where it is parked, and stepping rather than seeking inside
the crossover measured in `experiments/decode-experiments/results/02-*`.
Owns the seek race and its warmup discipline — the first hardware seek pays
CUDA warmup and misroutes the pair, recorded in the decode explorer's own
comment and a one-line trap to lose. Owns the probe cache keyed by machine
and source shape, moved out of `experiments/decode-experiments/explorer-logs/`
to a per-user location, because a verdict cached inside an experiment
folder is one the application cannot read.

A route returns a frame in its *source* form. It does not crop, scale or
convert; that is `forms.build`, and keeping it out of the route is what
lets one decoded frame answer for several forms.

May not know: what a crop is, what a store is, what a window is, that
anything runs in the background.

*Proved it:* six cases, passing, with `--broken` failing the one that can
see the difference. Software, hardware and hybrid return byte-identical
pixels for the same rows. Rows 0–19 of the source report absent, and row 20
is not what any of them hands back for row 0. `keyframe_at` lands on a real
keyframe at or before the request everywhere except the head, where the
keyframe before decodes to nothing and it correctly lands *after* — the
case a caller assuming otherwise gets wrong. The probe races from an empty
cache, writes a verdict, and a second open reads it instead of re-racing.

`--broken` restores the half-frame tolerance every predecessor carried, and
the result is worth stating plainly: **every one of rows 0–19 comes back
holding row 20's image**, and parity still passes, because both sides are
equally wrong. Parity alone was never enough, and this is the run that
shows it.

Cost is recorded rather than asserted, per ADR-0008: sequential stepping
and scattered seeking are timed as ordinary harness cases and live in
`experiments/substrate-checks/results/`. The probe's own verdict on this
machine agrees with what the decode explorer found about where hardware
seeks start winning, which is a cross-check rather than a new result.

### P2 — tiers — *landed*

`src/sieve/store/resident.py`, `.../spans.py`, `.../chunks.py`,
`.../coverage.py`; checked by `experiments/substrate-checks/03-tiers.py`

One deviation: reading is `spans.py`, shared, and `chunks.py` only adds the
write side. A proxy store is a `SpanStore` over a different directory with a
different producer, so there is no `proxy.py` here — the builder that fills
one is P5's, and giving it a reader of its own would have been the fourth
copy of a seek loop this phase exists to remove.

Owns what is held and what is on disk, all of it keyed by `(row, form
key)`. The resident store answers an exact get, a nearest-within-radius
get, and evicts to one byte budget across every form — a map and a lock,
never a decode. Nearest is a bisect over a sorted per-form coverage
structure rather than the explorer's `min()` over every key under the lock
on the GUI thread; the same structure makes "what is covered in this span"
cheap. Eviction takes a residency set and will not drop what is in it,
which is the whole of the retention policy and is why no form needs a
budget of its own. The chunk store encodes a completed span to one
intra file and serves rows back out; the proxy store is the same shape with
a different producer. Coverage is a recorded artifact these write and read,
never inferred from a present file, an absent gap, or an empty value —
`series.py`'s discipline applied to frames.

May not know: which tier should be asked, or in what order anything fills.
A store answers "have you got this, in a form that grades `EXACT` for what
I want" and "here it is". It does not choose.

*Proved it:* seven cases, passing, none of which needs footage — what a
tier does is decided by rows, forms and budgets. Two forms of one instant
coexist; eviction takes the least-recent unprotected frame and leaves a
protected one alone; a residency set larger than the budget leaves the
store over budget rather than dropping what it was told to keep, which is
ADR-0006's honest failure. `nearest` is checked against the linear scan it
replaces over the same data, because agreeing with the scan is the only
thing that makes the replacement safe.

**The case worth reading is `range`, and it found a real defect that both
explorers have.** Storing a grey frame as `yuv420p` applies the
limited-range convention on the way in — black is written as 16, white as
234 — while the read side takes the luma plane raw and does not undo it. So
a frame served from a persisted chunk differs from the same frame served
from memory by a contrast stretch, and nothing reports it: the array has
the right shape, the picture looks right, and any value computed from it
depends on which tier answered. That is exactly the hazard `form` states
its exact grade to prevent, one level further down, and it is invisible to
every instrument that measures time. Grey is now stored as `gray` and the
round trip is an identity within quantisation. The check tests black and
white rather than an average, because an average absorbs a squeeze.

`--broken` swaps the record lookup for the directory glob the explorers
use, and rows that were never written come back holding another chunk's
frames while a deleted file stays in the record forever. It also caught a
latent bug in the code under test rather than in the explorers: an
`except av.AVError` clause that does not exist in this PyAV version, so the
handler raised instead of handling. That path had never been reached.

### P3 — the record

`src/sieve/analysis/series.py`, `src/sieve/session/ledger.py`

Two records, moved and built respectively. `series.py` carries across as
written: values, an explicit coverage array, the pts table, the warm-up
boundary, the sidecar, the lock, and its own honest list of what it does
not yet do. The ledger is new-ish — the explorers' `RunLog` with the
matplotlib half left behind: every serve logs its task, the tier that
answered and its elapsed time on one session clock; every background
activity logs its span.

This is phase three and not phase eight on purpose. It is how P4 through P7
get debugged, it is where the decimation rule that keeps a looping session
from writing tens of thousands of play-hits lives
(`what-froze-the-felt-loop`), and it is the surface ADR-0008's waste count
later attaches to — a reason to get its shape right while nothing depends
on it, not a reason to build the waste count now.

May not know: anything. Both receive records.

*Proves it:* a series round-trips through save and load with its key
recovered from the sidecar rather than the filename; an uncovered row reads
as `None` and never as zero. Ledger records serialise and reload, and
decimation drops rows while keeping the count honest.

### P4 — declarations

`src/sieve/analysis/tool.py`

`tools.py`, moved. This was the phase I previously listed as deferred for
having no counterpart, which was wrong: it is ADR-0006 implemented, and
better specified than the ADR. A step declares the form it wants its inputs
in, the offsets it admits as a set, and whether it is evaluable anywhere or
only in order. `needs(row)` is what
must be resident to evaluate one position; `residency(active, rows)` is
what may not be evicted while serving a horizon — and the module is
explicit that confusing the two turns a sparse declaration into a fetch per
offset per position, which is the trap the ADR calls pathological.

Cost class is not declared; `classify` computes it from measurement, which
is ADR-0007 and is why the probe from P1 and the ledger from P3 both land
before this.

May not know: how anything is fetched, stored or drawn.

*Proves it:* the sparse-offset load (`lag_mhi`) has a reach wider than its
admitted set and both numbers come out right; `residency` over a moving
horizon unions to a working set rather than a point set; a tool key folds
the params its field uses and excludes params downstream of the series, so
a display-side threshold change reuses the stored values.

### P5 — producers

`src/sieve/store/build.py`, `src/sieve/session/frontier.py`

Owns the two things that run in the background, each split into a **pure
schedule** and an **impure worker** — which is the change that makes them
debuggable at all.

The proxy schedule answers "which batch next" from attention and the
present set; the builder launches ffmpeg, publishes finished segments by
rename, and kills and restarts on a redirect. The fill schedule answers
"which spans, in what order" from the window, the anchor, coverage and the
active residency; the frontier pulls those spans, admits through
`forms.build`, enqueues completed chunks for encoding, and yields its
decode bandwidth when a signal change asks for it.

May not know: what a request is. Neither serves anybody.

*Proves it:* both schedules are pure functions returning lists, so the
assertions are on order. The fill order is **the playhead's chunk first,
then the wrap** — that order is the whole of one finding, asserting it
costs nothing, and losing it costs a day. The builder schedule is exercised
with a fake launcher that touches files: no ffmpeg, no footage, assertions
on batch order, on a redirect discarding its incomplete batch, and on a
restart over a partial directory resuming rather than rebuilding. The
frontier runs against the fake route.

*Carried deliberately, and named as workarounds rather than design:* the
interpreter switch interval the explorer sets at import, which belongs in
application startup where it is visible; and the per-frame yield inside the
chunk encoder, whose removal condition is encoding in a subprocess the way
the proxy builder already does.

### P6 — the ladder

`src/sieve/session/ladder.py`

Owns choosing, and nothing else. Given a request — which row, in which
form, exact or not — plus what is resident and what the active declarations
need, returns a named decision. Pure function, table-driven test. The rules
it encodes:

- the GUI thread may block only for an exact request the user just
  released; everything else falls through to a cheaper tier
- inside the active window: resident beats persisted beats near-enough
  beats an `APPROX` derivation beats holding the current frame. A blocking
  miss is not on the ladder for a non-exact request
- outside it: the proxy answers where it exists, and a keyframe decode on
  the original answers where it does not — with the wanted form built from
  that decode and admitted, because it grades `EXACT`
- nothing that grades `APPROX` is admitted anywhere, which is `forms.py`'s
  own law and not a rule about routes

Coalescing belongs here too — discard rather than queue when requests
outrun the decoder, which `docs/decode/ideas.md` names and the decode
explorer carried as a toggle. In the session explorer it is a line inside a
GUI method, which is why it has never been tested.

May not know: how to decode, how to read a file, what a thread is.

### P7 — the session

`src/sieve/session/session.py`

Owns the running thing: source, stores, frontier, builder, series, ledger.
Executes what the ladder chose, holds the active window and the active tool
set as owned state, and enforces the one threading rule — a miss decode
never runs on the GUI thread. The crop rect is owned here and passed into
`form_for`, never read ambiently.

Every module-level constant in `session-explorer.py` lands here as state.
`_crop` reading a mutable global from three threads is the defect this
phase closes — and the deeper half of that defect is not the threading but
the ambience: a rect every call site must remember to fold into the key is
one that some call site eventually does not, filing a value under a key
that does not describe it. That is the invariant `05-provenance.py` exists
to check, and passing the rect makes it structural rather than checked.
It is why P0–P6 were written to take their inputs rather than read them.

*Proves it:* new harness scripts that put `src/sieve/` through what storage
01, 02 and 06 put the explorer through, labelled in their notes as a
different program — because they are, and a comparison that pretends
otherwise is worse than one that says so. Set beside the committed JSON in
`experiments/storage-experiments/results/`, the expectation is **parity at
the window tier and a gain at the hunt tier**: the window keeps the wipe
exp02 gave it, so its numbers should not move, while the hunt tier stops
re-decoding a proxy segment per request now that two forms can be resident.
A window number that moved names something dropped, and the candidates are
known — the switch interval, the encoder yield, the step-versus-seek
crossover, the playhead-anchored rotation. Each is one deletable-looking
line.

And `05-provenance.py`'s invariant runs against the real thing: a stored
value must be reproducible from the key it is filed under. It has a
deliberately broken producer to prove it can fail, which is the property
that makes it worth running here at all.

### P8 — the canvas

`src/sieve/gui/view/canvas/video_canvas/`, `src/sieve/analysis/surface.py`

`surfaces.py` moves as written; it already produces arrays at display size
and imports no Qt, so the widget that blits them is the only new code.
Owns showing a frame and drawing a field, pulling rather than being pushed,
never blocking, and — the constraint that belongs to `gui/` and not to the
substrate — participating in no layout negotiation. Content scales or
elides into geometry it is given. `what-froze-the-felt-loop` names a text
label as the thing that was resizing the video; that is a `gui/` defect the
substrate cannot prevent, so it is written where the widgets are.

First phase you can look at, which is late — and is the cost of the
arrangement above being testable before it is visible.

## Genuinely deferred

**ADR-0008's waste instrument.** The explorers count cost and never waste,
and this is the one piece with no implementation anywhere. It is nearer
than it looks: the predicted re-fetch that makes it falsifiable needs a
declaration to be predicted against (P4) and a record to be counted in
(P3), so after those two it is a comparison rather than a subsystem. The
ADR itself is settled before P0 so that P3 can pick a data model; only the
counting waits.

`tool-explorer.py` is ahead of the plan here and should be read before the
counting is built — it already carries five clocks with an explicit
unattributed remainder, and counters for avoidable fetches and unpainted
frames.

**A span-level answer from the series.** `series.py` names this itself: a
consumer asking whether a stretch is usable walks `runs` and `missing`, and
one that reads uncovered rows as zeros repeats the failure coverage exists
to prevent, one level further down. Wants a real consumer before being
designed for, and P6's ladder may be it.
