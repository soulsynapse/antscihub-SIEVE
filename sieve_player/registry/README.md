# sieve_player.registry

The catalogue of tools. A module is a tool if it has `SIEVE_TOOL = True` and a string `NAME`;
nothing else is required, and the registry never rejects one. Everything else is a facet, read
with `probe(tool, facet)`, which is `getattr(tool, facet, None)` and never calls the tool. None
means the tool did not say; consumers degrade and may show `hint(facet)`, the line that would
supply it. No facet has a meaningful None (pass-through is `PRODUCES = "same"`). A facet is in
`FACETS` only if something in `sieve_player` outside this package reads it. A selector, a tool
whose `PRODUCES` is `"path"` with no `EXPECTS`, says `select` instead of `run`, and `matches` if
it can count what its rule covers. A tool with `PATHS` has a path input per key, which a selector
feeds; the value is called with the picked file and answers the params to merge. A series tool
that steps says `step` beside `run`: handed the state it returned for the row before, None at the
first, one folded row and its index, it returns the next state and that row's share of `run`'s
result, so the shares accumulated over a series equal `run` over it; `run` stays mandatory and is
the oracle, tests/stepping.py holds a tool to it, and the registry only reports that `step` is
offered. A module that fails
to import is still an `Entry`, with the exception in `error`, so a broken tool shows up instead
of vanishing.

The types are whatever the tools say: `types(entries)` maps each to who produces and who expects it,
and the report prints that first. `CLASSES` is the one table written by hand: a class names the
types one body may serve alike, and `strains(entries)` lists each tool whose `EXPECTS` names more
than one type of a class and not all of them, with what it lacks. The report prints those lines
after the types; a line is a question for the tool's author, not a failure, since a refusal may be
principled, and a tool naming one type alone never strains. `pairs(entries)` then lists each two
tools that look like one tool declared twice: their `NAME`s equal once the table's types and classes
are removed, which is `verb(name)`, or most of the names their files bind at top level outside
`FACETS` shared, with the fraction. That line too is a question, since the bodies alone say whether
a pair is a merge or two operations over two units, and the names-shared threshold was tuned on one
pair, see docs/spec/tool-naming.md's Open items. `--check` fails if this list and
`__all__` differ, if a facet is read by nothing, if a type under `tools/` is produced or expected
by nothing, or if a class names a type no tool under `tools/` uses.

## Exports

- `MARKER`
- `FACETS`
- `Entry` -- `name`, `module`, `path`, `error`; `get(facet)`, `missing`, `ok`
- `is_tool(obj)`
- `probe(tool, facet)`
- `hint(facet)`
- `discover(*roots)` -- imports each `.py` under `roots` as `<dirname>.<stem>`, skipping a stem that begins with `_`: those are what tools share, never tools
- `types(entries, extra=())` -- type -> (producers, expecters)
- `CLASSES` -- class -> the types one body may serve alike
- `strains(entries, classes=CLASSES)` -- [(tool, class, the types it lacks)]
- `verb(name, classes=CLASSES)` -- the name less the table's types and classes
- `pairs(entries, classes=CLASSES, share=0.6, floor=3)` -- [(a, b, same verb, names shared, names in union)]

```
python -m sieve_player.registry [root ...]   # report; default root is tools/
python -m sieve_player.registry --check
```
