# Span

Keep only the frames in a range. Everything outside it is not in the answer, and
because the planner reads the range before the reader is opened, it is not
decoded either. The default range — wider than any video — keeps all of it.

## When to use it

**To tune against five seconds instead of five hours.** This is the span VISION
step 4 is about: pick a stretch where the behaviour you care about actually
happens, tune the chain against it until the graphs look right, then widen it and
run the lot. The graphs refill in the time it takes to decode those seconds
because the rest of the file is never read.

**To cut the parts that are not the experiment.** The minute before the lid goes
on, the handling at the end, the stretch where somebody bumped the table. A
detector run over them will find something, and what it finds is not behaviour.

**To split one recording into runs that are actually separate.** Two trials in
one file are two spans, and each carries its own bounds into its own cache
entries, so re-tuning one does not touch the other.

## Parameters

### `start`, `end`

Two frame indices, half-open: `start` is kept, `end` is the first frame that is
not. Frame numbers rather than seconds, for the reason the rest of SIEVE counts
in frames — a container's timestamps drift, and a span that means a different
stretch after a reload is a span that invalidates the tuning done against it.

The default is `start=0, end=4294967296` — past the end of any footage, so it
meets every video as the whole of it. That is what "no span" is: a value of these
parameters, not the absence of the node. It is written this way because the
length of the video cannot be typed by anybody who has not opened it, and the
graph is written by things that have not.

## Where to put it

**Last.** A span node narrows the whole run wherever it sits — the frames it
keeps are the frames the answer has, and every node in the graph computes the
same ones — so placement cannot change the result. What it changes is the cache.
A span at the root is folded into the key of everything below it, so nudging the
bounds recomputes the entire chain for frames whose pixels did not move. At a
leaf it invalidates only its own entries, and its own entries are copies.

This is the opposite of where a crop goes, and for an unrelated reason: a crop
has to sit at the root because its box is in its input's coordinates, and a span
has no coordinate problem at all.

Two span nodes in one graph are legal and mean the intersection. If it is empty,
the run is refused with both ranges named rather than completing over nothing.

## What it does not do

It does not shorten the video. The file is untouched; what changes is which
frames a run reads and reports. Writing the kept frames out as footage is a sink,
or a materialized crop artifact, and both are separate steps with a file at the
end of them.

It does not skip frames inside the range. Every frame between `start` and `end`
is decoded and computed. Keeping every tenth frame is a decimation, which is a
different filter and one that owes you an anti-alias filter with it.

It does not stop the lead-in being read. A filter that needs thirty frames to
settle still gets them, from before `start`, and they are discarded once they
have done their job. So a span near frame 0 is under-warmed and says so, exactly
as a clip near frame 0 always has been.

## Cost

Nothing. The kernel returns the frame it was handed, so there is no per-pixel
work and the cost model declares zero rather than a small measured number that
would really be call overhead.

What the node is *worth* is the decode it avoids, and that saving belongs to the
run rather than to the node: a span of 5 seconds out of an hour reads a
seven-hundredth of the frames. That is the largest single lever in the tool, and
it is why this is a filter you place first in your thinking and last in the
graph.
