---
title: The registration hint names two of three ElementKinds
priority: normal
phase: 1
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -k element_hint_names_every_kind -q"
opened: 2026-08-07
---

# The registration hint names two of three ElementKinds

`ToolSpec.__post_init__` refuses an array emitter that declares no element
meaning, and the message tells the author what to pass:
`element=ElementKind.PIXEL/BLOCK if this tool decides what one value is`
(`core/tool_base.py`, the `emits is ArraySpec and element is None` branch). The
enum has three members and `detect` declares `FRAME`, so the hint enumerates
two of three at the one place somebody meets the rule — a fixture author who
wants a per-frame scalar reads the message and does not learn that `FRAME`
exists.

This is the same defect
[the docstring one](elementkind-counts-two-members-over-three.md) fixed, at a
second site the docstring test does not reach: prose enumerating the enum that
the enum outgrew. It was not in that item's scope and did not ride along with
it.

`done_when` names a case rather than a literal string because the message has
to stay answerable to the enum the way the docstring now is: assert every
`ElementKind` member's name appears in the raised message, so a fourth member
fails the case instead of quietly not being offered.

## What landed

Both halves of the offer are now joined out of their enums —
`"/".join(member.name for member in ElementKind)` and the same over
`ElementRelation` — rather than typed into the string. The relation half was
not wrong today (it names both members), but it is the same clause of the same
sentence and the same defect shape, and leaving it hand-written would re-open
this item the day a third relation lands; the alternative was a second item
whose whole content is "do the other half of the string you were already
editing". That is the one thing here beyond what the criterion demanded, and
it is named for the review rather than folded in silently.

`test_the_element_hint_names_every_kind` in `TestElementMeaning`
(`tests/unit/test_tool_contract.py`) was shown failing against the unchanged
tree — `AssertionError: assert ['FRAME'] == []`, the missing member by name,
which is the defect stated as an assertion rather than a string ban.

```
$ uv run pytest tests/unit/test_tool_contract.py -k element_hint_names_every_kind -q
.                                                                        [100%]
1 passed, 79 deselected in 0.12s
```

The gate is green beside it: `ruff check` and `ruff format --check` clean on
both touched files, 730 tests.
