---
title: A source param names a folder, and several files are an ordering
priority: high
phase: 3
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests -q -k \"a_source_param_naming_a_folder or a_resolution_goes_stale_when_the_folder_changes\""
opened: 2026-08-09
---

# A source param names a folder, and several files are an ordering

Split out of
[the-stream-a-position-produces-is-resolved-not-declared](the-stream-a-position-produces-is-resolved-not-declared.md)
when that item closed at `119fb2c`. The fold it landed answers what a position
produces once the root has resolved; this is the other half of the same VISION
scenario, and the criterion above does not overlap that one — that item's names
the offer under a source resolved to *one* video, and everything here is about a
source resolving to more than one.

VISION's new-project scenario, either side of the sentence about the offer: the
user "swaps the source to the folder itself — SIEVE shows the folder as the
source, and the one video in it", then drops a second video in, comes back, and
SIEVE "re-reads the folders the project's own source params name; two files now
show in the source tool, and the box has changed to match".

**A source param has to be able to be a folder, and several files resolving from
one param has to stop being an error.** The landed source tool pins the opposite:
[the-first-source-tool-moves-the-three-single-root-assumptions](the-first-source-tool-moves-the-three-single-root-assumptions.md)
is `done` and carries `a_pattern_matching_several_files_is_refused` in its
criterion, its body stating the policy as "one resolving to several is refused
rather than ordered". That refusal was right for a pattern standing in for one
file and is the wrong answer for a folder, so what is owed is the distinction
rather than a reversal — and the ordering question the refusal was avoiding comes
back with it, since two videos concatenated in the wrong order is a silent wrong
answer rather than a failed run. Reversing the refusal outright would falsify a
`done` item's criterion, which is the signal that the distinction is the work.

**The re-read has a trigger nobody has named.** "Comes back to SIEVE" is a window
regaining focus, which is the first thing in the product whose input is neither a
user gesture nor a run — so it is view state that invalidates a resolution, and
the resolution is what `gui/streams.stream_specs` computes the whole offer from.
A stale offer is the visible failure; a stale *resolution* under a live offer is
the quiet one. `_reread_graph` is the existing invalidation point and its
docstring already enumerates its callers as "a project opening, and a step leaving
the chain", so a third caller is a change to that sentence as much as to the code.

These are one item rather than two because the second exists only to keep the
first honest: the resolution goes stale precisely because a file appeared in the
folder, which is the event VISION uses to define the feature. If the session that
takes this finds the focus trigger is a session-layer question with its own
subject, splitting is defensible — say so rather than building both badly.

What the *user* does with an ambiguous resolution — two files matching both a
concatenating tool and a folder of pre-cropped videos, offered "with the tool
picker display" — is not here. That is
[the-source-is-a-card-in-the-walk](the-source-is-a-card-in-the-walk.md), which
already draws the distinction and delegates the resolution itself outward.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests -q -k "a_source_param_naming_a_folder or a_resolution_goes_stale_when_the_folder_changes"
    1204 deselected in 0.96s
    exit: 5

## 2026-08-09: built as one, and where the ordering stops

Both halves landed together; the split the body permitted was not taken, because
the focus trigger has no subject without a resolution to invalidate and the
resolution has no way to be shown wrong without it.

**The distinction, not the reversal.** `tool_base.named_files` is the one rule
both source tools and `checkpoint` read: a param naming a folder resolves to
every file in it, lexicographically, several allowed; a param that is a pattern
resolves to its matches and still refuses several.
`a_pattern_matching_several_files_is_refused` is untouched and green.
`tool_base.one_named_file` is where a reader that hands over one file's frames
meets an ordering, and it refuses on its own terms — the pattern's message says
narrow it, the folder's says nothing reads a sequence of files yet. That is where
the ordering stops today, and it is the honest stopping place: `concatenate` is
VISION's illustration and not a shelf entry, so nothing here may read one. What
is settled ahead of it is the *order*, which was the question the old refusal was
avoiding.

**The re-read.** `MainWindow.changeEvent` calls `_reread_graph` when the window
becomes the active one, and `_reread_graph` grew a fifth fact —
`resolve_source.resolved_sources`, the ordered files each source root names. The
docstring's caller sentence names the third caller and says why it is unlike the
other two: the first four facts are folds over a document only this window
writes, and this one read the filesystem.

Not built, and named rather than assumed: nothing paints `resolved_sources`.
That is folded into
[the-source-is-a-card-in-the-walk](the-source-is-a-card-in-the-walk.md) along
with the extension-class question a flat unfiltered folder listing opens.

A measured landmine is
[findings/2026.08.09-a-shown-window-in-one-added-case-aborts-the-gui-run-at-exit](../findings/2026.08.09-a-shown-window-in-one-added-case-aborts-the-gui-run-at-exit.md).
