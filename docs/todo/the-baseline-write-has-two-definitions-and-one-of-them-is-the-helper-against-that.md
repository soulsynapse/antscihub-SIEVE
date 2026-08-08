---
title: The baseline write has two definitions and one of them is the helper against that
priority: low
phase: "7"
status: done
gated_on: nothing
done_when: "uv run python scripts/mutation_sweep.py --file src/sieve/core/pipeline_model.py --mutant 'node.model_copy(update={\"params\": frozen_value({**node.params, **params})}) ==> node' -- uv run pytest -q tests/unit/test_pipeline_model.py tests/unit/test_intents.py"
opened: 2026-08-08
---

# The baseline write has two definitions and one of them is the helper against that

`edited_params` exists, by its own docstring, so that "a caller holding the
pieces rather than a `Project` performs the identical edit rather than a
paraphrase of it". 07.3 needed the baseline half of that edit alone and wrote it
out again: `with_param_default` and `edited_params` now each contain

    node.model_copy(update={"params": frozen_value({**node.params, **params})})

byte for byte. Two copies of the schema-v1 answer to "how does a node's baseline
move", in the one module whose job is to hold exactly one, three hundred lines
apart. They agree today, so nothing is wrong with either result — the cost is
entirely future: the first change to the baseline rule that is made through one
of them leaves the other stating the old rule, and both are exercised by live
tests, so nothing goes red for the disagreement.

The fix is a shared write both call. It is behaviour-preserving, which is why
the criterion is a mutation and not an assertion: no test can distinguish one
definition from two, and a case comparing `with_param_default`'s result to
`edited_params`' would be green before the work and green after it
(`findings/loop/2026.08.08-a-consistency-guard-as-a-criterion-is-green-on-both-sides-of-the-work.md`).
`mutation_sweep` refuses an anchor that occurs more than once, so the command
above exits 1 today naming the duplication itself, and exits 0 exactly when the
expression has one home and a test kills its removal. Run on the unchanged tree
it prints `anchor occurs 2 times`.

The second half of the same edit, which no criterion can witness on its own:
07.3 also relaxed `_replacing`'s signature from two required `Replicate`
arguments to two independently-optional ones, so that `with_param_default` could
substitute a node without touching the replicates. The two are one pair, not two
options — `replicate` supplied without `new_replicate` writes `None` into
`Project.replicates`, and `_replacing` builds with `model_copy` rather than
`model_validate`, so nothing refuses it and the invalid document reaches
whatever reads it next. No caller does this and none is likely to; the point is
that the signature stopped saying so. One optional pair argument says it back,
and once it is one argument the half-supplied state is unconstructible, so there
is nothing left for a case to assert — and `CLAUDE.md` records that no type
checker is installed, so nothing else reads the annotation either. That is why
it rides along here rather than carrying a criterion of its own: it is real and
it is uncheckable, which is the pairing that gets an observation dropped rather
than recorded.

Filed to Phase 7 rather than Phase 2, though both lines are schema-v1's edit
surface. `phase` is the ordering, and filing back is for groundwork a later
phase stands on: Phase 7 does not stand on this. Both copies agree, the
signature admits a state nothing reaches, and 07.4 onward build correctly on the
module as it is. Filed to Phase 2 it would be selected ahead of every remaining
Phase-7 step, which is a claim about the build order that nothing here
supports.
