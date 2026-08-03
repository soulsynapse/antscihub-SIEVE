# Session: PAR-0005 at judgment — the deliberate attack

Status: Open
Date: 2026-08-03

The occasion: PAR-0005 sits Proposed, rewritten in one sitting by the
same agent that dismantled its predecessor, never read by anyone who did
not also author it. A deliberate attack was convened at judgment
(PAR-0001: "arriving holding the answer and trying to break the draft"),
by fresh eyes with the charge to verify the empirical claim rather than
accept it. Kendrick's convening words: "Its necessity argument rests on
one empirical claim, and you should verify it yourself... If you
conclude the gap is mostly two decode-path bugs plus a person who moved
on, say so — the Context loses its footing and the Decision is left
standing on much narrower ground." And: "Do not soften the verdict to
be agreeable, and do not manufacture objections to look rigorous."

Open because the ruling is Kendrick's; the attack itself is complete.

## Exchange 1 — the v1 citations verified, and the one that misreads

Every v1 citation resolves to what the record says is there.
`core/video.py` ~383–417 builds the split/crop/scale/format/pad/vstack
filtergraph and ships gray16le over the pipe;
`ReplicateVideoSource`'s docstring states the 48 MB BGR frame avoided
to retain ~8% of 5.3K footage. `core/preprocess.py` holds the z-score
collapsed to `g*a + b` with "2.3–3x" measured (lines 234–253), the
`accepts_native_gray16` path skipping the 0–255 conversion because a
positive scale cancels from a z-score (112–142), and the skipped
resize at scale 1 with "610 us per call" (153–159).
`core/stream_buffer.py` is the block-grid ring the wavelet reads.

One citation is misread, in the PAR and in the frozen primary it
inherits from (SESSION-2026-08-03-shape-algebra-edges.md, Exchange 6).
`video.py:232-237`'s 0.364 vs 3.80 are **RMS error in grey-levels
against a float reference** — an accuracy measurement. "It records
that the *order* inside that graph is worth 10×," placed in a
paragraph explaining why v1 runs faster, reads as speed and is not.
The frozen record keeps its error; the correction lands in the PAR.
The misread does not kill the sentence's use — scale-before-format is
still a rewrite rule that lived only in a comment — but it is evidence
of the opposite kind than claimed: an ordering rewrite that *changes
the answer* 10-fold, which is Exchange 4's problem below, not a speed
win.

## Exchange 2 — the v2 citations verified, and the attribution

Every v2 citation resolves. `decode/reader.py:112-118` (`_downscale`)
shrinks after a full-resolution decode; `reader.py:86-95`
(`_position_at`) grab-forwards; `decode/prefetch.py` opens up to four
`VideoReader`s (`INFERRED_WORKER_CAP = 4`), each thread claiming
interleaved indices, so each reader grabs through the frames the
others claimed and decode work scales with worker count;
`pipeline/executor.py:54-81` materializes a full `Frame` per node per
frame in DAG order with no fusion.

Attribution, formed independently and then compared with the record's:
the dominant term of the gap is the decode path. v1 runs one
sequential FFmpeg process and crosses the pipe at working size; v2
runs ~4× the decode work, materializes full-resolution BGR in Python,
and resizes per frame. A working-size FFmpeg reader with one
sequential decoder recovers most of the gap with no representation at
all — which the record's own primary already concedes (Exchange 6:
"Two of the three are decode-path defects, not architecture gaps").
The Python-side wins the comments record (z-score affine 2.3–3× of
the preprocess span, 610 µs resize skips, the gray16 path) are real,
measured, and second-order against the decode term.

So the prompt's suspicion is confirmed in substance but was already
half-conceded in the text. What the Context still owes: its framing —
"The occasion is measured rather than argued" followed by the speed
gap — lets a reader believe the *magnitude* evidences the rewrite-rule
system. It does not. The magnitude evidences a decode-path design; what
evidences this record is the *diagnosis cost* — the gap "went
undiagnosed through a whole rewrite" because every rule lived in a
person and in comments, and finding them again took reading both repos
side by side. The narrower ground the Decision actually stands on:
serializability is required by the recipe hash regardless (PAR-0009),
conformance costs nothing (`Opaque(fn)`), and rules that are values
with tests survive redesigns where comments do not. That ground is
sufficient. The Context should claim it and not the speed.

## Exchange 3 — the proof standard contradicts the record's own evidence

The main attack. The Decision's third paragraph: "The executor may
rewrite only where the representation proves the answer is unchanged:
affine composed with affine is affine." The Consequences: "an affine
chain evaluates identically fused and unfused."

Affine-compose-affine is a proof about the *map*, not about sampled
pixels. Sampling once through the composed map is not bit-identical to
sampling twice — the design session says so itself (Exchange 3:
"fusion changes pixels... define semantics at the logical level,
require the planner to be semantics-preserving within a stated
tolerance, and ship a preference that disables fusion"), then
contradicts itself two exchanges later (Exchange 5's property test:
"bit-identical fused and unfused"). PAR-0005 inherits the
contradiction without naming it, and v1's own measurements — the
record's chosen evidence — show the flagship rewrites changing answers:
one-pass sampling differs from two-pass (Exchange 5's own "filters
twice and softens" bonus paragraph), the format-order rule is a 10×
*accuracy* difference, and FFmpeg's area scaler measures 0.364 where
OpenCV's measures 0.321 against the same reference.

Read strictly, "answer-preserving by proof" forbids the very fusion
the record exists to enable. Read loosely, it licenses fusion only via
an unstated convention. The repair is to state the convention: the
answer is *defined* at the logical level — the composed map is the
semantics, and pass count is an implementation detail — which is the
design session's own Exchange 3 position. That choice has teeth and
the record must own them: the naive evaluator is then not the
semantic reference for resample chains unless it too samples once
through the composed map, and the property test restates as identity
under the logical semantics rather than identity between two
evaluation strategies. Until this paragraph is redrawn, the record's
central sentence does not support its central examples.

## Exchange 4 — offload can never clear the silent bar as written

"A subgraph may be lowered to a foreign engine... subject to the same
proof requirement; it is also... the largest available win." No
foreign engine is bit-identical to the local path — v1 measured the
divergence. So under the record's own standard, its largest win can
never be silent: every FFmpeg offload is "user-initiated, shown, and
recorded," a swap ceremony per pipeline, where v1's equivalent was
default-on. Either that is the intent — the record should say so
plainly — or the proof bar admits "equivalent under the defined
logical semantics within the pinned tolerance," which is the same
repair as Exchange 3. The paragraph currently claims a win its own
rules withhold.

## Exchange 5 — the redraw dropped a ruled-in benefit and left citations dangling

Exchange 2 of the prior session ruled in the five-shapes-on-paper
compromise for a stated benefit: "telling a contributor what the
intended factoring is, so the first tracker is not written as an
`Opaque` holding a global. That benefit is a record's, not a module's,
so the record keeps all five." Kendrick: "your argument for the
smallest version with insurance is good." The Exchange 10 redraw then
cut the vocabulary to what is proved — affine map, the sequential
bit, `Opaque` — deleting the guidance benefit without naming the
reversal. Later supersedes earlier within a session and the redraw was
requested, so this is a wobble to acknowledge, not a violation; but
the tree still carries the ghost: two `DEFERRED.md` entries cite
PAR-0005 for text it no longer contains ("stated in PAR-0005 as the
intended factoring"; "PAR-0005 states the shapes beyond `Resample`
and `Opaque` as provisional until their first instance"). A record
under judgment whose tree citations point at its previous body is a
mismatch to fix at or before acceptance — and if the guidance benefit
is still wanted, its home is now those DEFERRED entries' own text or
PAR-0003's how-to ("writing an op"), and something should say so.

## Exchange 6 — the four pipelines against the redrawn record

The method that broke the predecessor, rerun against the rewrite.
Spatial-neighborhood ops (Sobel, blur, erosion): `Opaque`, resting
state, honestly covered. TRex background subtraction: a subgraph
admitted by measurement, routed to PAR-0012, covered. The
frames-to-rows reduction: conceded as Challenge 1 — with one typing
slop: `Opaque` is stated as "frames in, frames out," and a reduction
is frames in, rows out, so the concession's own resting place doesn't
type. `Opaque` should be restated as "no structure exposed, nothing
authorized" rather than a video→video signature.

Challenge 2 (data-dependent domains) is overstated as written. "Run
centroid tracking only within the detected windows" is expressible as
ordinary dataflow: the windows are an upstream *product* with its own
hash, the tracking op consumes them as an input, and the recipe hash
already includes upstream output hashes (DESIGN-SESSION.md,
Exchange 1). Expressibility and hashing do not fail; what fails is
rewrite reasoning *across* the gate edge, which is just a barrier —
and barriers are the vocabulary's normal case. The challenge should
narrow to what actually stands: no rewrite crosses a data-dependent
edge, and a pull-based evaluator gets the skip-what's-not-requested
win without any representation change. Kendrick confirms or corrects;
if this reading holds, the record's honest-concessions section is
carrying a concession it doesn't owe.

## Exchange 7 — smaller defects, and the seam with PAR-0008

- `Opaque(fn)` holds a callable and therefore does not round-trip,
  so the serializability guard's sole exception is also a hole in the
  hashing story: an `Opaque` op's recipe hash must come from tool
  identity plus a hand-bumped version (Exchange 1's `impl_version`),
  and nothing says so. One sentence, owed to PAR-0009 or PAR-0007 at
  their drafting, named here so it isn't rediscovered.
- The record now spans the representation *and* the executor's
  authority, bordering PAR-0008. The seam that keeps both records
  revisable independently: PAR-0005 owns what a form authorizes —
  the property carried by the value; PAR-0008 owns when and whether
  the executor exercises it — the peephole discipline, the naive
  evaluator, the evidence threshold. Stating that seam in one
  sentence in each record is cheaper than the merge question
  recurring.

## Exchange 8 — verdict

**The record stands, on narrower ground, and is not ready to accept as
written.** It names a real system (the op representation and the
rewrite authority it carries); the system is load-bearing (the tool
contract's return type, the hash's input, the offload surface); it
earns its place in ARCHITECTURE.md at acceptance exactly as its
Consequences plan; and three of its four claimed how-tos are
followable once code exists. Nothing in it belongs in PAR-0007,
PAR-0009, or PAR-0012 beyond what its Consequences already route.
It should not be cut further: the redraw already cut to the
load-bearing parts, and the attack found no paragraph doing no work.

What acceptance waits on, in order of weight:

1. The Decision's third paragraph redrawn to state where the answer is
   defined (the logical level, per DESIGN-SESSION.md Exchange 3),
   what "proof" then means, and what happens to the
   fused-equals-unfused property test and the reviewer's
   disable-fusion check (Exchange 3 above).
2. The offload paragraph states which bar it clears — swap ceremony
   per pipeline, or proof under the defined semantics with pinned
   tolerance (Exchange 4).
3. The Context corrects the 10× misattribution and re-grounds the
   occasion on diagnosis cost rather than speed magnitude
   (Exchanges 1 and 2).
4. `Opaque` restated as no-structure-exposed; Challenge 2 narrowed or
   defended; the `Opaque` hashing sentence routed; the two dangling
   `DEFERRED.md` citations re-anchored; the PAR-0008 seam stated
   (Exchanges 5–7).
