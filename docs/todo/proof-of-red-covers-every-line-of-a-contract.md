---
title: Proof of red covers every line of a contract
priority: low
phase: 0
status: done
gated_on: nothing
done_when: "uv run pytest -q tests/unit/test_contract_lines_go_red.py tests/unit/test_import_contracts.py"
opened: 2026-08-07
---

# Proof of red covers every line of a contract

00.2's gate added one violating edge per contract and watched each go red,
which proves the contract is wired up and leaves every other line in it
untested. The one line that went untested was also the only one that could
not have fired — a forbidden module that does not exist is inert
(`findings/2026.08.06-a-forbidden-module-that-does-not-exist-is-inert.md`,
`findings/loop/2026.08.06-one-red-per-contract-certifies-the-contract-not-its-lines.md`).

Per-line proof is the honest version: each forbidden module, each layer edge,
each exception, violated in turn. That is a lot of red for a contract file
that grows slowly, so the version worth building is the one that generates
the violations from the contract file rather than listing them by hand — a
test that reads `.importlinter` and asserts every line in it can fail cannot
go stale when a line is added.

That inert line has since been proven red by hand, against a copy of the tree
with `core/ops/` planted in it
(`tests/unit/test_import_contracts.py`,
`findings/2026.08.07-an-inert-forbidden-entry-can-be-proven-red-against-a-copy.md`).
The copy is the part the generated version inherits: it means a generated
violation does not have to be hostable by the real tree either.

The trigger has fired. It was a contract gaining a line, and the layers
contract has gained `sieve.mutual` — so the newest line in the file is
currently proven by the same one-red-per-contract gate that certifies nothing
about it individually.

Done is `tests/unit/test_contract_lines_go_red.py`: for every line the config
carries — each `forbidden_modules` entry against each of its `source_modules`,
each adjacent pair in `layers` — a violation planted in a copy of the tree and
the linter run against it, red, naming that contract. Read out of
`.importlinter`, so a line added later is covered the day it lands rather than
the day someone remembers. `test_import_contracts.py` stays in the criterion
because the generator does not subsume it: its supported-path case asserts what
`allow_indirect_imports` leaves *legal*, which is not a red and has no
generated form.
