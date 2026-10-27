# sieve_player.registry

The catalogue of tools. A module is a tool if it has `SIEVE_TOOL = True` and a string `NAME`;
nothing else is required, and the registry never rejects one. Everything else is a facet, read
with `probe(tool, facet)`, which is `getattr(tool, facet, None)` and never calls the tool. None
means the tool did not say; consumers degrade and may show `hint(facet)`, the line that would
supply it. No facet has a meaningful None (pass-through is `PRODUCES = "same"`). A facet is in
`FACETS` only if something in `sieve_player` outside this package reads it. A selector, a tool
whose `PRODUCES` is `"path"` with no `EXPECTS`, says `select` instead of `run`, and `matches` if
it can count what its rule covers. A module that fails
to import is still an `Entry`, with the exception in `error`, so a broken tool shows up instead
of vanishing.

`--check` fails if this list and `__all__` differ, or if a facet is read by nothing.

## Exports

- `MARKER`
- `FACETS`
- `Entry` -- `name`, `module`, `path`, `error`; `get(facet)`, `missing`, `ok`
- `is_tool(obj)`
- `probe(tool, facet)`
- `hint(facet)`
- `discover(*roots)` -- imports each `.py` under `roots` as `<dirname>.<stem>`

```
python -m sieve_player.registry [root ...]   # report; default root is tools/
python -m sieve_player.registry --check
```
