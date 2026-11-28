# sieve_player.registry

The catalogue of tools. A module is a tool if it has `SIEVE_TOOL = True` and a string `NAME`;
nothing else is required, and the registry never rejects one. Everything else is a facet, read
here and nowhere else in the player: a module asks by a name that says what is asked, `expects(tool)`,
`cuts(tool)`, `fold_of(tool)`, and calls a facet the registry answered for; `tests/test_seams.py`
holds the player to it. `probe(tool, facet)` is `getattr(tool, facet, None)`, never calls the
tool, and is this package's and the report's. None means the tool did not say; consumers degrade
and may show `hint(facet)`, the line that would supply it. No facet has a meaningful None
(pass-through is `PRODUCES = "same"`). A facet is in `FACETS` only if something in `sieve_player`
outside this package calls it or one of its `READERS`. The package imports nothing of the player. A selector, a tool
whose `PRODUCES` is `"path"` with no `EXPECTS`, says `select` instead of `run`, and `matches` if
it can count what its rule covers. A tool with `PATHS` has a path input per key, which a selector
feeds; the value is called with the picked file and answers the params to merge. A cutting tool
with `CUT_BY` has one input more, which no row is read through: the result wired into it over
each cut the node reads is what its `cut_extents` is handed, once a cut, and a result over a cut in
time counts its rows from that cut's first, the rows answered of it lifted to the footage's by the
player. `cut_extents` is handed the footage's rows third, None before they are known. A cutting
tool says `run` only where it changes what it reads: one with none hands each row down as it read
it and is in no key below it, so a cut that moves moves no result of a cut that did not; one with
a `run` is keyed as any tool is. A `cut_extents` that raises cuts nothing: its node is refused, its standing what was
raised, and no node below it is fed. A series tool
that steps says `step` beside `run`: handed the state it returned for the row before, None at the
first, one folded row and its index, it returns the next state and that row's share of `run`'s
result, so the shares accumulated over a series equal `run` over it; `run` stays mandatory and is
the oracle, tests/stepping.py holds a tool to it, and the registry only reports that `step` is
offered. A module that fails
to import is still an `Entry`, with the exception in `error`, so a broken tool shows up instead
of vanishing, and so is a tool whose `PARAMS` cannot be read, under its own name.

A tool says each param once, in `PARAMS`: its default, the kind of its value, and its range or its
choices. The player makes a node's first params and a plain settings widget of it, a row a param
that says a kind, in the tool's order; a tool with a card of its own says `settings` and builds
its rows of the same declaration. A param a `draw` or a card alone reads says
`"changes result": False`: it is in no key, so a change to it computes nothing again, and the
player hands `run`, `step`, `key_params`, `reach_in_rows`, `cut_extents`, `cut_file`, `cut_files`, `select` and `matches` the
params without it, so a tool that reads one there raises and no result follows it. One left
unsaid is in the key and handed over. A tool whose rule a mark cannot say, a param read only
under some value of another, says `key_params`, which answers in place of the params and is
trusted.

The types are whatever the tools say: `types(entries)` maps each to who produces and who expects it,
and the report prints that first. `--check` fails if this list and `__all__` differ, if a facet is
read by nothing, or if a type under `tools/` is produced or expected by nothing.

A tool's category is derived, never declared: `category(tool)` reads the facets by an ordered list,
source, measure, relate, convert, transform, the first rule that fits deciding, so a tool
lands in a Tab menu group the day it is written and nobody files it; docs/spec/tool-naming.md
argues the list. `description(tool)` is the first sentence of its docstring less its label, and
`signature(tool)` its types in and out, what the menu shows beside the name. The report prints the
category beside each tool.

## Exports

- `MARKER`
- `FACETS`
- `WIDGET_FACETS` -- what a settings widget may have beside `changed`, `params()` and `set_params()`, each name to the line that supplies it; `tests/test_seams.py` holds the pane, the window and the tools to these names
- `Entry` -- `name`, `module`, `path`, `error`; `get(facet)`, `missing`, `ok`
- `is_tool(obj)`
- `probe(tool, facet)`
- `hint(facet)`
- `discover(*roots)` -- imports each `.py` under `roots` as `<dirname>.<stem>`, skipping a stem that begins with `_`: those are what tools share, never tools
- `code_print(tool)` -- a digest of its file and of every file of its folder whose name begins with `_`, as they lie now, each parsed and less its docstrings, so a comment's edit leaves it; no key holds it
- `imported_print(tool)` -- that digest as `discover` found it when it first imported the module: the code the process runs
- `types(entries, extra=())` -- type -> (producers, expecters)
- `CATEGORIES` -- the groups in the Tab menu's order
- `category(tool)` -- the group a tool's facets put it in
- `description(tool)` -- the first sentence of its docstring, unlabelled
- `signature(tool)` -- what it reads and hands out, as "gray, mask → blobs"
- `READERS` -- facet -> the readers below that answer of it
- `name(tool)`
- `by_name(tools)` -- name -> module, of a mapping or the modules
- `kind(tool)` -- `KIND`, "frame" unsaid
- `expects(tool)` -- `EXPECTS` as a tuple, the one place it is made one; None for a tool that expects nothing
- `produces(tool)` -- `PRODUCES` as written, "same" among what it may be
- `KINDS` -- the kinds of value a declared param may say
- `params(tool)` -- `PARAMS`, name -> what it says, read or a ValueError naming the param
- `defaults(tool)` -- name -> default, of `PARAMS`
- `changes_nothing(tool)` -- the params that say `"changes result": False`
- `computed(tool, given)` -- a node's params without those: what its key holds and its computing is handed
- `settings_of(tool)` -- its `settings`, or None
- `inputs(tool)` -- `INPUTS`, name -> a tuple of types
- `optional(tool)`
- `static(tool)`
- `paths(tool)` -- `PATHS`, name -> loader
- `is_selector(tool)`
- `cuts(tool)` -- whether it has `cut_extents`: it cuts what it reads, whether or not it writes a file
- `hands_down_what_it_reads(tool)` -- whether it cuts and has no `run`: the player hands down each row as the node read it and leaves the node out of every key below it
- `cut_extents_of(tool)` -- its `cut_extents`, or None
- `cut_by(tool)` -- (name, a tuple of types) of `CUT_BY`, or None
- `reach_of(tool, given)` -- (rows before, rows after) its result at a row reads, of `reach_in_rows`; None a side without bound, both unsaid
- `serves_cut_file(tool)` -- whether it has `cut_file`
- `names_cut_files(tool)` -- whether it has `cut_files`
- `steps(tool)`
- `draws(tool)`
- `fold_of(tool)` -- its `fold`, or None
- `key_params_of(tool)`
- `pick_of(tool)`
- `matches_of(tool)`

```
python -m sieve_player.registry [root ...]   # report; default root is tools/
python -m sieve_player.registry --check
```
