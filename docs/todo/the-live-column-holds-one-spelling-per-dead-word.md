---
title: The live column holds one spelling per dead word
step: "03.2.1"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_id_spelling.py -q"
opened: 2026-08-07
---

# The live column holds one spelling per dead word

`DEAD_IDENTIFIERS` in `tests/unit/test_tool_id_spelling.py` matches a dead word
as a case-insensitive substring with no boundary, and the escape hatch is a
single live spelling per row that is stripped before the search. That was
sufficient while the only row was `filter`, whose collisions in v3 are rare. The
`clip` row added at 02.2 is a different case: `np.clip` is the ordinary way to
bound an array, and `rescale`/`normalize` (04.3) are the tools most likely to
reach for it — as would any clamp in `core/ops/`. `clipped`, `clipping`, and
`np.clip` all fire, and the exception list cannot absorb them because
`test_the_exception_list_is_empty` asserts it stays empty for a reason that is
still right.

One live slot cannot hold `np.clip` *and* `clipped`, so the first real
collision is a change to the table's shape, not a row edit — the live column
becoming a tuple of spellings, or the match gaining word boundaries with the
substring case handled per row. Decide which when the collision arrives and
there is a real line to test against; deciding now would be picking a shape for
a call nobody has written. The failure mode if it is not decided is worse than
noisy: the cheap way out under a red gate is to rename a legitimate `np.clip`
call, which makes the array math worse to read in order to keep a rename gate
green.

## 2026-08-07: the collision arrived, from `decode/` and not from `clip`

03.2 ported `decode/` and `storage/crop_writer.py` byte-identical and the gate
went red on 28 lines: `roi` 14, `filter` 13, `clip` 1. Twenty-seven of them are
a different word. `filter` is FFmpeg's (`-filter_threads`,
`-filter_complex_threads`, `LoweredPrefix.filtergraph`) and `quiet.py`'s, whose
whole subject is filtering one line out of a byte stream. `roi` is a local
bound off `LoweredPrefix.ffmpeg_roi` and the parameter of
`lowered.roi_parts(roi: ROI)` — a region typed as the live `ROI`, not v2's
`Replicate.roi` field. `clip` is `crop_writer.py`'s docstring saying a caller
may stream a whole video clip through it.

The twenty-eighth is real: `reader.py:135` calls `max_width`
`never a pipeline filter`, which is the dead word in its dead sense.

## Reviewed 2026-08-07: that twenty-eighth line is not a question

03.2's run left that line as a standoff between the gate and the porting
discipline and said only Kendrick could break it. It is not one. PLAN.md's
porting discipline defines verbatim as identical modulo import paths *and*
ADR-1's renames, so the rename was licensed on that comment before the file was
copied, and `core/types.py` is the case already decided the same way — it sits
in the same verbatim list and its blob differs from v2's by exactly six lines
of renamed prose, five of them found by this gate at 01.5. Apply the rename to
`reader.py:135` and move on; nothing about it waits on a ruling.

What does wait is the other twenty-seven, and they are the whole of this item.
Those lines are FFmpeg's, PyAV's, and English's word rather than v2's, and no
row edit reaches them — `-filter_threads` and `ffmpeg_roi` carry the dead word
as a morpheme, so a word-boundary match fails them too. What the shape has to
express is which vocabulary a line is speaking, and `decode/` speaks two.

## 2026-08-07: the shape is two tables, and eleven lines needed it, not twenty-seven

Sixteen of the twenty-seven are v2's word after all, and the classification
above is where this item was wrong: a dead spelling inside a compound whose
other half is foreign reads as foreign, but `ffmpeg_roi` is not FFmpeg's name
for a rectangle — it is `Replicate.roi` with its consumer prefixed on, and v3
already spells that thing `region`. Those, `roi_parts`, the four locals off
them, the two cache-key strings, and `LoweredScale.filter_id` (which had no
foreign half at all) rename under the same license as `reader.py:135`. See the
finding for the line-by-line split.

The eleven that remain got the shape. Five are tokens FFmpeg owns whole, and
the live column became a tuple to hold them beside the ADR slug — a token
excuses one spelling and leaves the rest of the file readable. Six are prose in
a module whose subject is the foreign sense, which no token reaches, and those
are declared per `(module, word)` in `SPEAKS_A_FOREIGN_VOCABULARY` with a
staleness assertion so a module that stops speaking FFmpeg loses its waiver.
Both tables are needed because `lowered.py` held FFmpeg's `filtergraph` and
v2's `filter_id` at once: a module-wide waiver would have buried the second.

`src/sieve/` is the walked tree, so nothing about this is confined to
`decode/`: the ported files are simply the first ones written in a vocabulary
SIEVE does not own. Any word FFmpeg, OpenCV, or PyAV also uses will land the
same way. The gate is red at HEAD until this closes, which is why it is a step
and no longer a pool item.
