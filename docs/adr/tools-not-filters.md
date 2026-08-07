---
title: Tools, not filters — and the identity values are frozen
adr: 1
position: "01.01"
status: settled
decided: 2026-08-06
---

Pipeline steps are **tools**: field, package, and class names rename
(`tool_id`, `sieve.tools`, `ToolSpec`), while the identity *values*
(`"crop"`, `"detect"`, …) stay exactly v2's.

Why: the values are what the v2 importer maps against and what parity
fixtures reference — renaming them would make every golden array and every
saved project lie about what produced it. The rename is names only, and the
`tool_id` spelling gate (Phase 1) holds it shrink-only.
