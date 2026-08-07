---
title: v2 projects do not import
adr: 15
position: "02.02"
status: settled
decided: 2026-08-06
---

v3 reads no v2 file: there is no `compat` package and no importer, and no
module anywhere spells a v2 field name — schema v1 is written as if v2 never
existed.

Why: the importer's license (the 2026.08.05 finding revision) answered
whether it *could* be built, not whether it was needed, and it isn't: the
only user's v2 projects are few, and the product's own premise — the tuning
loop is fast — makes re-creating a project cheaper than maintaining a
one-way translator with its fixtures and spelling exceptions. The frozen
identity values keep re-creation mechanical
([tools-not-filters](tools-not-filters.md)). Phase 5's oracle survives the
deletion: build the equivalent pipeline by hand in both versions and diff
outputs at the product level. Revived only by a real v2 project that must
come over, at which point [compat-spells-v2](compat-spells-v2.md) is the
shape to revive.
