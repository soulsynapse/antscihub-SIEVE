---
title: A crop becomes a file that verifies itself
step: "05.1"
status: done
gated_on: nothing
done_when: "uv run pytest tests/integration/test_materialize.py -q"
opened: 2026-08-07
---

# A crop becomes a file that verifies itself

`pipeline/materialize.py` port-with-rename: one replicate's crop cut to an
FFV1 file that opens in any player and opens in SIEVE as an ordinary source
with an identity of its own. The record it registers is schema v1's (02.1),
so the parts that touch the model are re-derived while the cutting and
verification are copied.

The verification pass is the half that must not be trimmed. v2 measured a
*lossless* encoding whose pixels came back wrong on every frame through the
same reader that reads everything else — right shape, wrong values — and the
guard is what stands between that and a dataset nobody can tell is wrong
(v2's `docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md`). A run that
cannot verify refuses to register the record; it does not register it with a
warning.

The artifact is a child source, not a proxy for its parent: nothing writes a
record claiming the parent's identity, and a run against the artifact roots
off the file's own source identity with no region. That sentence is what
keeps 03.4's key derivation unchanged by this item — materializing a crop
changes where a result lives and never what it is.

`tests/integration/test_materialize.py` holds **8 cases**; 8 rows in the
table. The criterion once named `tests/unit/test_crop_artifact.py` for v2's
nine record cases as well, and both halves of that were wrong by the time
04.1 finished: the filename now holds 04.1's pixel round trip on a different
subject, and the record half already landed with schema v1 — `TestCropRecords`
and the relocation case in `test_pipeline_model.py` assert seven of v2's nine,
leave the eighth implied by the matching rule rather than asserted, and the
ninth is a v4-document migration v3 has no schema for
(`findings/2026.08.07-the-crop-record-half-of-v2s-artifact-file-landed-with-schema-v1.md`).
Nothing about the record model is this item's to add; what is left here is
the cutting and the verification pass.
