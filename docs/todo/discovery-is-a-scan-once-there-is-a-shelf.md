---
title: Discovery is a scan, once there is a shelf to scan
step: "03.7.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_discovery.py -q"
opened: 2026-08-07
---

# Discovery is a scan, once there is a shelf to scan

`sieve/tools/__init__.py` finds tool modules by scanning the package rather
than importing them by name, and `tests/unit/test_tool_discovery.py` ports
v2's `test_filter_discovery.py` onto it. Struck from 01.2 at review — every
case in v2's file needs a tool on the shelf, and 02.4 is where the first one
arrives.

Two of v2's six cases are about `ParamsBase` rather than about discovery
(params survive a JSON round trip; `canonical_json` is byte-identical in a
*fresh interpreter*) and they come here because `DownsampleParams` is their
fixture. The subprocess one is the only check anywhere that would catch a
salted `hash()` or an `id()` leaking into a cache key input, and it has had
no home since 01.2 cut its fixture — do not fold it into the in-process
canonical-form assertion `test_tool_contract.py` already has, which cannot
see the failure it exists for.

The two guidance cases (`every_discovered_tool_has_guidance_markdown`,
`every_guidance_file_answers_the_three_questions`) are *dropped*, not
deferred: there is no per-tool document in v3, and guidance is a `ToolSpec`
field arriving in Phase 7 with the expander that reads it. Port the four that
survive — the scan imports no tool module, checked by parsing `__init__.py`
as an AST rather than as text; every discovered tool declares a caption; and
the two `ParamsBase` cases.

This lands before 03.8 rather than in a pool because `sieve run` names a tool
by id in YAML and the registry has to be populated by then, and the one thing
the registry's docstring forbids is a manifest that adding a tool must edit.
