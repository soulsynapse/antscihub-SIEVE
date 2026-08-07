---
title: doc_index has no case over its own command line
priority: normal
phase: 0
status: open
gated_on: nothing
done_when: "uv run pytest tests/docs/test_doc_index.py -q -k \"mint_flag or the_index_build_refuses_a_drifted_item\""
opened: 2026-08-07
---

# doc_index has no case over its own command line

`main()` has never been called by a test. Nothing noticed until
`minting-an-item-cannot-overwrite-one` landed two behaviours whose whole value
is that they sit in the path every session runs, and the review's mutation
sweep found both deletable with the suite green: cutting `lost = tracked_drift()`
and its `raise` out of `main()`, and making `if args.mint:` unreachable, each
leave `tests/docs/test_doc_index.py` at 62 passed. `mint` and `tracked_drift`
themselves are well covered — five semantic mutants inside them all died — so
what is missing is exactly the wiring, which is the half the item argued for:
"the check belongs where the index is built, since that is what every session
runs."

Both behaviours are real today; the review drove them by hand and both refuse
with exit 1 and a message naming the recovery. So this is declared behaviour
with no case rather than a defect, and it is worth writing as two cases through
`main(argv)` rather than through the functions again — a tmp repo whose
`opened` has moved makes the index build exit 1, and `--mint` over a taken slug
exits 1 while leaving the file it would have replaced intact.

`doc-index-writes-what-it-can-and-next-reads-no-docstring.md` wants `main()`
restructured, and it will need the same harness; whichever lands first should
leave it behind for the other.
