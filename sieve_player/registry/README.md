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
and the report prints that first. `--check` fails if this list and `__all__` differ, if a facet is
read by nothing, or if a type under `tools/` is produced or expected by nothing.

A tool's category is derived, never declared: `category(tool)` reads the facets by an ordered list,
source, cache, measure, relate, convert, transform, the first rule that fits deciding, so a tool
lands in a Tab menu group the day it is written and nobody files it; docs/spec/tool-naming.md
argues the list. `description(tool)` is the first sentence of its docstring less its label, what
the menu shows beside the name. The report prints the category beside each tool.

## Exports

- `MARKER`
- `FACETS`
- `Entry` -- `name`, `module`, `path`, `error`; `get(facet)`, `missing`, `ok`
- `is_tool(obj)`
- `probe(tool, facet)`
- `hint(facet)`
- `discover(*roots)` -- imports each `.py` under `roots` as `<dirname>.<stem>`, skipping a stem that begins with `_`: those are what tools share, never tools
- `types(entries, extra=())` -- type -> (producers, expecters)
- `CATEGORIES` -- the groups in the Tab menu's order
- `category(tool)` -- the group a tool's facets put it in
- `description(tool)` -- the first sentence of its docstring, unlabelled

```
python -m sieve_player.registry [root ...]   # report; default root is tools/
python -m sieve_player.registry --check
```
