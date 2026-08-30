# tool-experiments

Where SIEVE finds out what happens to the frame stack once something other
than the player asks for a frame, and what a tool leaves behind when it does.
`decode-experiments` settled what a frame costs to get; `storage-experiments`
settled what it costs to keep, and measured the tuning loop end to end with a
single consumer. This folder is the layer both of those deferred.

It is not a plan any more. Most of what it set out to answer is answered,
three of those answers are ADRs now, and what remains here is the evidence,
the substrate the answers produced, and an explorer to feel them in. Read the
ADRs for what is settled; read this for why.

## What it settled

**A value is recorded where its inputs landed** (ADR-0005). Nothing that
draws may decide what gets recorded, because what a renderer selects depends
on what the machine had time to draw.

**A declaration is a fetch plan** (ADR-0006). What a step names, what is
held, and what a re-fetch means are the ADR's to say; restating them here is
how the two drift apart. What this folder measures against it is `tools.py`'s
offsets and `series.py`'s writes.

**A cost class belongs to the pairing** (ADR-0007). Measured where it runs,
never declared, so a weaker machine falls back deliberately instead of
chasing a figure set on other hardware.

Two more decisions live in module docstrings rather than ADRs, because they
are about how this code is built rather than about the architecture.
`forms.py` fixes the canonical construction and the rule that **derived is
for looking at, decoded is for recording**. `surfaces.py` holds the two
presentation rules: reduce to display resolution once per data change, and
keep the live surface and the report surface as different code.

## The experiments

Each writes to `results/` carrying its build, machine and probed footage.
Numbers are not restated here — the result files are where a later
measurement supersedes an earlier one by sitting beside it.

1. `01-paint-cost.py` — what drawing a tool's output costs. Settled the
   overlay draw order (resize the field, then colour-map: cheaper, and the
   only order whose colour bar is honest), and put the rasteriser out of the
   live loop rather than off its thread. Ran first because an uninstrumented
   paint reads as a slow store.
2. `02-form-derivation.py` — does a held frame answer a wanted form more
   cheaply than a decode. The answer inverts between the two regimes the loop
   runs in, and that inversion is the result: derivation pays only where
   decode is expensive, which is exactly where the dominating form is too
   heavy to hold much of. So the domination test belongs to the hunt tier,
   and the window tier keeps the wipe it already has.
3. `03-free-while-hot.py` — the marginal cost of riding along on a decode
   that was happening anyway. Falsified declared cost classes, which produced
   ADR-0007, and caught three wasteful field implementations on the way,
   which is the second thing an experiment is for.
4. `04-under-load.py` — the same with the loop's own background work running.
   Every tool inflates by about the same factor, so the one that gets felt is
   simply the largest number rather than a specially fragile one.
5. `05-provenance.py` — the check the others cannot perform. One invariant: a
   stored value must be reproducible from the key it is filed under. It runs
   against a deliberately broken producer (`--broken`) as well, because a
   test that has never failed has no demonstrated power.

## What this folder got wrong

Recorded because the wrong version is more appealing than the right one, and
a later reader will otherwise re-derive it.

The overlay originally wrote the series. The argument was that a field has to
be recomputed in order to be drawn, the frame it is drawn from was already
decoded, and the number falling out of it is the same number a background
pass would write later at full price. Every clause of that is true. The
conclusion — that the drawing may therefore do the recording — inverts the
dependency, and makes what is recorded depend on paint cost, compositor
cadence and machine load.

It survived four experiments because all four measured cost, and a value
filed by the wrong producer costs exactly what the right one costs. No timing
instrument can see a provenance error. What found it was a question about
shape rather than about speed.

Two smaller ones went the same way. A cost class was declared by each tool
until measurement showed the class belongs to the pairing. And a
`write_sweep` sat in `series.py` documenting a warm-up guarantee that nothing
called — the same shape as a test that has never failed, and worse than no
guarantee at all.

The standing rule from all three: **a tool that does not exist may be a
workload and may never be evidence.** Designs argued for here from invented
tools have twice failed to survive contact; designs *tested* here against
invented tools have been useful every time.

## The substrate

`forms.py` — what a stored frame is, and when one already on hand can answer
for another: the canonical construction, and the exact/approximate admission
line.

`tools.py` — what a step declares before anything schedules or draws it: the
form it wants, the inputs it admits as offsets from the position being
computed, its field and its reduction. `classify` computes a cost class from
measurement; nothing declares one.

`series.py` — one float per position per step, coverage recorded rather than
inferred, a pts table saying what a row means, and its own lock. Its known
gaps are stated in its docstring: nothing answers "is this *span* usable",
and there is no third state for provisional values.

`surfaces.py` — drawing at display resolution from data reduced to it, and
nothing Qt.

The tools are `absdiff`, `dis_flow` and `lag_mhi`, and they are loads rather
than proposals. `absdiff` and `dis_flow` straddle the free/not-free boundary
so every fork that reads a cost class fires at least once, and `lag_mhi` is
the only one whose input set is not its reach, which keeps that distinction
tested rather than merely stated.

## The explorer

`tool-explorer.py`, forked from `storage-experiments/session-explorer.py` and
deliberately not rewritten, so the existing baseline subtracts from it. It
adds a tool, an overlay that draws a field and records nothing, the series
band, five clocks with an explicit unattributed remainder, and the counters —
avoidable fetches, unpainted frames.

`--smoke` drives it headless end to end; `--rate` measures whether the loop
keeps its rate and where the interval goes, with the window shown. What
neither can do is judge whether the overlay reads at its ceiling, whether the
decimated series band looks like signal or like noise, or what an overlay
should do under load. The three overlay policies are display-only, have never
been shown to differ, and are kept because that last question is real and
unanswered.

## The rule for a result

Import `../decode-experiments/harness.py`, repoint `harness.RESULTS` here,
keep every per-iteration sample, discard a stated warm-up. A case that could
not run says so in its notes; a silently absent case reads as a case that
came out equal.

Two rules this folder adds. **A number claimed about the loop is taken in the
loop, and a number taken in isolation says so** — a microbenchmark is often
the right instrument and may never be quoted as a felt cost. And **every
stored value names its writer, once, in the module that owns it**, which is
the practice `05-provenance.py` exists to check.

## What is still open

The reduced-series tier is built and unpriced: what a series costs to write,
to read back time-columnar, and to invalidate, against the null hypothesis of
one array per key. Yielding is unmeasured — a run the user started may make
the loop worse and may not keep doing so once they come back. A batch
protocol, one request carrying a set of positions sorted by keyframe, is
untried. And the loop's achieved rate falls short of its target whenever
anything draws over it, by an amount that is not the work: `--rate` reports
the interval and the remainder, and the cause is characterised rather than
fixed.

## Running

    uv run --group experiments python experiments/tool-experiments/<name>.py

Footage comes from `video-tests/`, gitignored. Derived files the other folders
make are inputs here; an experiment that needs one either finds it or makes it
and says which in its notes.
