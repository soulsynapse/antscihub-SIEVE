---
title: The template guard names its three subjects by hand, so a fourth template is uncovered the day it lands
priority: normal
phase: "00"
status: done
gated_on: nothing
done_when: "uv run pytest \"tests/docs/test_doc_index.py::test_the_template_guard_covers_every_template\" -q"
opened: 2026-08-07
---

# The template guard names its three subjects by hand, so a fourth template is uncovered the day it lands

`246507d` made the anti-vacuity guard per template rather than summed over the
three, which is the repair its item asked for. What it did not change — because
the assertion it replaced had the same shape inline — is where the *subject
set* comes from:

```python
TEMPLATES = (doc_index.TODO_DIR, doc_index.FINDINGS_DIR, doc_index.ADR_DIR)
```

and the expectation the counts are compared against names `todo`, `findings`,
and `adr` as literal keys. Both are written out. The guard's declared subject is
"each template", and `docs/**/_TEMPLATE.md` is three files today, so the two
agree — but they agree by coincidence of the tree, not by construction. A fourth
folder that gains a template is silently outside the guard, and nothing goes red
to say so: the new template can state the rule and show neither form, which is
exactly the state the todo template was in and the state this guard exists to
catch.

This is the hand-enumeration shape the loop findings keep naming — a sweep or a
check is only over what someone remembered to list, and the omission leaves no
trace. Derive the set from the tree instead: glob `docs/**/_TEMPLATE.md`, and
build the expected mapping from the folders found rather than from three names
typed above it, so adding a template adds a case.

`done_when` names a test that does not exist, so it is red today for the right
reason. It should assert the *derivation*, not a count — a test that hard-codes
the same three names in a third place has moved the problem rather than fixed
it.
