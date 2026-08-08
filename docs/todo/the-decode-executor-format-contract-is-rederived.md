---
title: The decode/executor format contract is re-derived, not ported
status: open
priority: normal
phase: 3
gated_on: nothing
opened: 2026-08-07
---

# The decode/executor format contract is re-derived, not ported

v2's `tests/unit/test_decode_format.py` is the only place the format
handshake between `decode/` and the executor is checked, and 03.2's review
struck it from that item's criterion because it is not a decode test. Its
three subjects are `graph_needs_chroma` (03.3's `dag`), `source_key` (03.4's
`cache_key`), and `FormatMismatchError` (03.6's `executor`), and no item's
`done_when` names it now — so without this item the contract ships untested
and nothing goes red.

It cannot be moved by editing another item's criterion, which is why it is an
item. Four of its imports do not survive the port: `sieve.backend.dispatch`
(PLAN.md drops `backend/`), `core.filter_base` and `core.filter_registry`
under their v2 names (01.2 renamed them and cut fields), and
`core.pipeline_model`, which is re-derived as schema v1 in Phase 2 and which
`adr/v2-does-not-import.md` forbids any v3 module from spelling in v2's
vocabulary. The `Pipeline`/`Node`/`Edge` graphs its cases build are therefore
rewritten against schema v1, not translated — hence phase 3, after the schema
exists.

What must survive the re-derivation is the assertion, not the fixture: a graph
whose tools need chroma pulls a chroma decode and one that does not pulls
luma; `source_key` changes when the decoded format changes and not otherwise;
and the executor *refuses* a frame whose format disagrees with the plan rather
than converting it. That last one is the reason the file exists — a silent
conversion is a wrong-but-green result of exactly the kind the loop cannot
detect. It runs on a `_OneFrame` fake in v2, never on `synthetic_video`, and
that should stay: the contract is about disagreement, and a real decode cannot
be made to disagree with itself on demand.
