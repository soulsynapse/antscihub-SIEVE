---
title: The hand-written proofs of red are generated too, and the docstring says they are not
priority: low
phase: 0
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_contract_lines_go_red.py -q -k proven_red_twice"
opened: 2026-08-08
---

# The hand-written proofs of red are generated too

`tests/unit/test_import_contracts.py` says of itself that
`test_contract_lines_go_red.py` "plants the same package to cover every other
line the file carries", and that what stays behind is "the pair of claims that
generator has no shape for". The second half is true — that some `forbidden`
contract carries the edge at all, and that `allow_indirect_imports` leaves the
supported route legal, are both read out of the config and neither has a
generated form. The first half is not. The generator walks every
`forbidden_modules` entry against every one of its `source_modules`, so it
already collects `pipeline-computes-nothing__sieve_pipeline_imports_sieve_core_ops`,
both `session-computes-nothing` lines and
`decode-knows-no-schema__sieve_decode_imports_sieve_core_pipeline_model` — the
four edges `test_the_entry_fires` proves by hand. It proves them harder, too:
it asserts `f"{name} BROKEN"` where the hand-written case asserts only that the
contract's name appears somewhere in a report that lists every contract's name.

`todo/proof-of-red-covers-every-line-of-a-contract.md` ruled on this when it
landed the generator — "`test_import_contracts.py` stays in the criterion
because the generator does not subsume it: its supported-path case asserts what
`allow_indirect_imports` leaves *legal*". The supported-path case, not the fire
case. The docstring was not brought along, and 07's contract work read it and
added three more subsumed cases on its authority, each a `copytree` of the
package and a linter subprocess
(`findings/loop/2026.08.08-a-file-whose-docstring-claims-a-division-of-labour-the-generator-has-outgrown.md`).

Done is the file proving what only it can prove. The criterion names a case in
the generator's file rather than in the file being cut, because a criterion
inside the module losing cases is one an empty module satisfies: assert of every
edge in `test_import_contracts.EDGES` that the generator holds a case for it,
*and* that the hand-written module exposes no lint-running red for it. Then the
docstring says what the split now is, and a fifth edge added later costs one
config-reading case rather than two.
