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
key.

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

Part 6 of the review says what would make E1 the wrong first: "that the count finds few settings
no `run` reads and the six places, read whole, agree in all but the csv's name". The count finds
three, one name. The six were read at their definitions; they agree but for the csv's name and the
breadth of the held file's stamp.

Not known: how often a held file is lost to an edit under `tools/`, and whether that, a toggled
`outline`, or something neither of these is what Kendrick feels as a result made again. The log
does not show it and nothing here measures it.
