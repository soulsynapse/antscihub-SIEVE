# A held file and an edited tool

2026-11-17. `docs/spec/what-a-node-declares.md` has a held file good under its keys alone, its
runs saying what code made them. `docs/findings/experiments/2026-11-17-a-held-file-and-an-edited-tool.py`
reads every held file under `video-tests/` as it lies with `held.py:File.load`, then drives a
player offscreen over a six-row clip and copies of `gray`, `reduce` and `smooth` in a folder of
their own.

| held file | begins with | runs | rows | nodes | a result says its code |
| --- | --- | --- | --- | --- | --- |
| `GoPro clip single v5.json.series` | (5, 5de15f59...) | 2 | 22616 | csv, reduce, smooth | no |
| `GoPro clip single.json.series` | (5, 85076f8d...) | 1 | 11308 | csv, reduce, smooth | no |
| `GoPro clip.json.series` | (5, d23ae5af...) | 1 | 11308 | reduce, smooth | no |
| `purb-168-178.json.series` | (5, 18389aea...) | 1 | 590 | count, size, track, travel | no |
| `purb-settings.json.series` | (5, d23ae5af...) | 87 | 202117 | count, size, smooth, track, travel | no |
| `test.json.series` | (5, 5de15f59...) | 1 | 30579 | reduce, smooth | no |

Six files under four digests of the tools' folder, none of them the folder's as it lay at this
run, and every one read back. Under the stamp they were written with, a player opened on any of
them would have read none.

The player:

| after | marked |
| --- | --- |
| the window's run held | none |
| `smooth.py` edited | smooth |
| `gray.py` edited | gray, reduce, smooth |
| the document closed and opened again, one run read back and the window served of it | gray, reduce, smooth |
| the held results let go, none held and the file loading as none, and the window walked again | gray, reduce, smooth |

The last row is the process's own: it imported the three tools before either edit and runs them
as imported, so what it walks after the let go is again made under code that is not the files'.
A player started after the edits is the one whose walk clears the mark, and this run started
none.

Not measured: what `window.py:PlayerWindow._show_stale` costs a call. It stats each node's tool
file and the folder's underscore files and reads one again only where its size or time moved,
and it runs wherever the strip's held bar is drawn again.
