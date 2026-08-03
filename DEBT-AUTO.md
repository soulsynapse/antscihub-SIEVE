# SIEVE automatic ledger

Generated; never hand-edit. Regenerate: `python -m sieve.debt write`

format-version: 3
marker-rule: v2

| path | qualname | stamp | reason |
| --- | --- | --- | --- |
| `docs/par/0006-param-vs-preference.md` | `<file>` | 20260802T225557Z | rationale for param vs. preference, discussion owed before drafting; governs until acceptance: DESIGN-SESSION.md Exchange 2 |
| `docs/par/0007-tool-contract.md` | `<file>` | 20260802T225558Z | rationale for the tool contract; claims at acceptance ARCHITECTURE.md invariant 1's archive/PLAN.md Phase 1 decision 2 citation and README's Exchange 1 citation (contracts derive from Params); governs until acceptance: DESIGN-SESSION.md Exchange 5 as rebuilt, and Exchange 2 |
| `docs/par/0008-executor.md` | `<file>` | 20260802T225559Z | rationale for the executor; governs until acceptance: DESIGN-SESSION.md Exchanges 3, 4, and 6 |
| `docs/par/0009-intent-progress-and-store.md` | `<file>` | 20260802T225600Z | rationale for the intent/progress split and the store, discussion owed before drafting; governs until acceptance: DESIGN-SESSION.md Exchanges 1 and 5 |
| `docs/par/0010-handles-and-materialization.md` | `<file>` | 20260802T225601Z | rationale for handles and materialization, merge-into-store question open; governs until acceptance: DESIGN-SESSION.md Exchange 2 |
| `docs/par/0011-selection-mechanism.md` | `<file>` | 20260802T225602Z | rationale for the selection mechanism, needs refinement, merge-into-executor question open; governs until acceptance: DESIGN-SESSION.md Exchange 7 as rebuilt by Exchange 8 |
| `docs/par/0012-harness.md` | `<file>` | 20260802T225603Z | rationale for the harness; whether it genuinely exists as a system, unbuilt and possibly argued against elsewhere, is its first question; governs until acceptance: DESIGN-SESSION.md Exchanges 8 and 9 |
| `docs/par/0013-gui-type-dispatch.md` | `<file>` | 20260802T225604Z | rationale for GUI type-dispatch and the closed vocabularies, owed elaboration to be perfectly clear; governs until acceptance: DESIGN-SESSION.md Exchanges 1 and 2 |
| `docs/par/0014-pipeline-construction.md` | `<file>` | 20260802T225605Z | rationale for pipeline construction; governs until acceptance: DESIGN-SESSION.md Exchanges 2, 6, and 7 |
| `docs/par/0015-run-semantics.md` | `<file>` | 20260802T225606Z | rationale for run semantics, boundary against the shape algebra open; governs until acceptance: DESIGN-SESSION.md Exchanges 3 and 4 |
| `docs/par/0016-format-versioning.md` | `<file>` | 20260802T225607Z | rationale for SIEVE format versioning and migration, SIEVE-facing formats only and likely stricter (repo-machinery formats are PAR-0002's); governs until acceptance: DESIGN-SESSION.md Exchanges 1 and 9 |
| `docs/par/0017-enforcement-in-tests.md` | `<file>` | 20260802T225608Z | rationale for enforcement-lives-in-tests, never convention, gated on PAR-0003's design settling what the explicit enforcement is; claims at acceptance README's Exchange 6 citation; governs until acceptance: DESIGN-SESSION.md Exchanges 1, 5, and 6 |
| `docs/par/0018-layout-settlement.md` | `<file>` | 20260802T225609Z | rationale for the layout settlement, citing the component records; governs until acceptance: archive/PLAN.md Phase 3 |
| `src/sieve/executor.py` | `render` | 20260802T023503Z | render(node, frame): pull-based single-frame evaluation, including the LRU frame cache the pull path requires to feel correct; ARCHITECTURE.md 'The executor', DESIGN-SESSION.md Exchange 4 |
| `src/sieve/gui.py` | `<module>` | 20260802T023504Z | GUI two panes: Params-derived config pane, view-rendered canvas with ROI overlay bound to the param field; ARCHITECTURE.md 'The GUI', DESIGN-SESSION.md Exchange 2 |
| `src/sieve/kernel.py` | `<module>` | 20260802T023505Z | five-shape op algebra as one unit (Resample, PixelMap, Window, Fold, Opaque), vocabulary v1 under additive revision; ARCHITECTURE.md 'The components', DESIGN-SESSION.md Exchanges 3 and 5 |
| `src/sieve/pipeline.py` | `<module>` | 20260802T023506Z | pipeline file format and loader: intent-only DAG of steps, per-step schema_version, migration registry, unknown-field preservation; ARCHITECTURE.md 'The pipeline', DESIGN-SESSION.md Exchange 1 |
| `src/sieve/store.py` | `<module>` | 20260802T023507Z | content-addressed store: recipe-hash addressing over the logical graph, size-budget aging, no invalidation; ARCHITECTURE.md 'The store', DESIGN-SESSION.md Exchange 5 |
| `src/sieve/tools/base.py` | `Tool.lower` | 20260802T023508Z | Tool.lower(p): params to an op graph in the five-shape algebra; ARCHITECTURE.md 'Tools', DESIGN-SESSION.md Exchange 5 |
| `src/sieve/tools/base.py` | `Tool.view` | 20260802T023509Z | Tool.view(p, out): declared view over the closed vocabulary; ARCHITECTURE.md 'The GUI', DESIGN-SESSION.md Exchange 5 |
| `src/sieve/tools/crop.py` | `<module>` | 20260802T023510Z | crop tool: Params (ROI regions), lower -> Resample, view -> Image with ROI overlay; ARCHITECTURE.md 'Tools', DESIGN-SESSION.md Exchange 2 |
| `src/sieve/views.py` | `<module>` | 20260802T023511Z | closed view vocabulary v1 (image, mask, points, paths, vectors, regions, series strip) under additive revision; ARCHITECTURE.md 'The GUI', DESIGN-SESSION.md Exchange 5 |
| `tests/test_conformance.py` | `<module>` | 20260802T023512Z | conformance suite: params round-trip, migration corpus, fused-vs-unfused and Window cold-vs-sweep property tests; DESIGN-SESSION.md Exchanges 1 and 5 |
