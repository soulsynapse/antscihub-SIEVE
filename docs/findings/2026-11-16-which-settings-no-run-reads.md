# Which settings no run reads

2026-11-16, the code under `sieve_player/` and `tools/` as `cf063108` left it. This is the count
`docs/systems-review.md` leaves open under E1 and names in part 6 as what says whether E1's fourth
step, the marks, is worth a change of keys. Nothing was run but the one-off and grep; the player
was not started.

## The count

`python -X utf8 docs/findings/experiments/2026-11-16-which-settings-no-run-reads.py tools` reads
each tool's `DEFAULTS` and follows its computing facets (`run`, `step`, `fold`, `cut_file`,
`cut_files`, `select`, `matches`) by name through the module and the folder's `_*.py` files.

Of 86 settings declared by the tools, 3 are read by no computing facet, and all three are
`outline`: in `blobs.py`, `filter.py` and `track.py`, each read by that tool's `draw` alone.
`attach.py` declares a fourth `outline`, which its `run` reads, as what a mark is held inside.
`region.py`'s `shapes`, `choice`, `quality` and `serve clip` are read by `cut_file`, and by its
`key_params` the key of a region that runs holds its plate and its rect alone.

What the count cannot see. A setting is counted as read where its name is a literal anywhere the
computing reaches, so one read only under some value of another, `top_hat.py`'s `inner` at 0 or a
bound typed blank, is counted as read; a mark on a setting could not say such a case either, and
`key_params`, being a function of the params, can. A param no `DEFAULTS` declares is not counted:
the five `draw`s of part 5's A11 that read an `outline` nothing sets are in no document and in no
key. Nor is a `DEFAULTS` a tool imports: `csv.py` takes its from `tools/_csvfile.py`, the one-off
counts it as none, and its one setting, `beside footage`, is read by the Write widget alone, by a
reading of both files on 2026-11-17. `csv.py` has no `key_params`, so that setting is in its
key. By the one-off and that reading together, 4 of 87.

## What a kept thing is good under, the six of A19

Read at each one's definition and docstring, and not at every caller.

| place | good under | a store of a node's result |
| --- | --- | --- |
| `plan.py:_key` | the upstream key, the tool's name, its params or `key_params` | the memo and the held runs |
| `held.py:stamp` | `held.VERSION` and `held.tools_print`, a digest of every `.py` file in the folders the tools were loaded from; `held.py:File.load` answers no runs under another | the held file |
| `tools/_cutfile.py:key` | the footage's print, the extent cut, the encoder's arguments | no: a file of footage, served as footage by its own print |
| `tools/_csvfile.py:key_line` | the plan's key, the rows, and the footage by its file's name | an export a node wrote |
| `decoder.py:_times_file` | the footage's print | no: a table of the file's frame times |
| `window.py:PlayerWindow._taken` | a path and its mtime | no: whether a path loader is run again, held in memory |

Three of the six answer for something that is no result of a node, and each of those is named by
what it is of. Of the three that are, the csv's line differs from the others in naming footage by
a file's name, which the review has. The held file's stamp is the one not met there: it is good
under the bytes of every file in the tools' folder, so an edit to any tool, or to a comment in
one, leaves every document's held file serving nothing at its next opening, whichever tools the
document holds.

## What this bears on

The count sizes one thing, what a mark on a setting, E1's fourth step, would take out of a node's
key as the tools stand: three settings by the one-off, and `csv.py`'s fourth. It does not size what one key that every kept thing and
every job answers to is worth, and it is no test of E1.

What Kendrick said he feels, reading the ledger's classes on 2026-11-16, is that whether a change
empties something upstream is "seemingly random" and that the tree has "leaned towards just
invalidating as the default". A setting no `run` reads is one way that comes about. The tree holds
others, each a rule of its own beside the plan's key, and it is their being several that reads as
random:

- the held file, let go whole by an edit to any file under the tools' folder (above);
- a bare walk, ended by changes that do not concern it, by his word (the review's C9 and H4; the
  code that ends it was not read here);
- a csv, which names its footage by a file's name and says nothing of the tools it was written
  under (above; whether its card then calls a stale one current was not read).

Each is a place that answers "is this still good" by something other than the key, which is what
E1 is for. So the count being small argues for the form of the fourth step, `key_params` on three
tools serving as well as a mark, and against nothing else in the entry.

Not known: how often each of these is met in a day's work. The log does not show it and nothing
here measures it.
