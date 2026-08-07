---
title: doc_index has no case over its own command line
priority: normal
phase: 0
status: open
gated_on: nothing
done_when: "uv run pytest tests/docs/test_doc_index.py::test_the_index_build_refuses_a_drifted_item tests/docs/test_doc_index.py::test_mint_over_a_taken_slug_exits_one_and_leaves_the_file tests/docs/test_doc_index.py::test_every_gate_is_reported_and_none_of_them_stops_a_write -q"
opened: 2026-08-07
---

# doc_index has no case over its own command line

`main()` had never been called by a test until `ae49e8f`, and the two cases it
brought — a bad docstring costs one target and never `--next` — leave the rest
of the command line where it was. Three behaviours run in the path every
session takes and are asserted by nothing:

1. A tracked item whose `opened` has moved makes the index build exit 1. The
   review of `minting-an-item-cannot-overwrite-one` found `tracked_drift`'s
   call site deletable with the suite green; `ae49e8f` moved that call from
   `main` into `gates` without adding the case, so it is still deletable.
2. `--mint` over a taken slug exits 1 and leaves the file it would have
   replaced intact. Same sweep, same result: `if args.mint:` was made
   unreachable and nothing failed.
3. `gates()` reports every problem rather than the first, and none of them
   stops a target being written. This is the whole argument of `ae49e8f`'s
   second half and it is the least covered thing in the file — this review
   replaced the body of `gates` with `return []` and all 64 cases in
   `tests/docs` still passed, so the four repo-wide refusals reach `main`
   through nothing a test can see. `assert doc_index.gates() == []` on the
   live repo is satisfied by a function that always returns `[]`.

All three are real today — each was driven by hand and behaves as declared —
so this is declared behaviour with no case rather than a defect. Write them
through `main(argv, repo=...)` against a tmp tree rather than through the
functions again: `tracked_drift`, `mint` and each of the four gate predicates
are individually well covered, and what is missing is exactly the wiring.

The criterion names the three cases as node IDs rather than a `-k` expression
because a `-k` over three alternatives is satisfied by any one of them.
`_tree_with_a_bad_docstring` in the test module is the harness to build on.
