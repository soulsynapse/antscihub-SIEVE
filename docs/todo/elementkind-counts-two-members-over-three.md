---
title: ElementKind's docstring counts two members over three and promises a third that already landed
priority: high
phase: 1
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -k element_kind_docstring_counts_its_own_members -q"
opened: 2026-08-07
---

# ElementKind's docstring counts two members over three

`ElementKind` in `core/tool_base.py` defines `PIXEL`, `BLOCK` and `FRAME`. Its
third paragraph opens "Two members, and the second is not speculative padding",
names only `block_signal` and `downsample`, and closes "A third member arrives
with the tool that needs it and not before." All three members and that sentence
landed together in `10434bb`, so the promise was false in the commit that wrote
it — `detect` declares `FRAME` at `tools/detect.py:564`.

Two separate wrongs in one paragraph. The count is arithmetic. The growth
promise is worse, because it reads as a live constraint on whoever wants a
fourth member and it describes a discipline the enum never followed: the
replacement has to say what the three members are and drop the promise rather
than re-date it, since a rule the file broke on arrival is not a rule.

Not cosmetic and not a prose-bloat item. A docstring stating a member count the
enum contradicts is a claim that isn't true, and it was read as evidence before
it was read as a defect — the argument over which axis carries a meaning like
"generated background"
([the first source tool](the-first-source-tool-moves-the-three-single-root-assumptions.md))
leaned on the growth promise until the enum was checked, and both readings had
to be re-argued on their own merits afterwards.

`done_when` names a case rather than a grep because the general shape is worth
having once: the docstring states a count, the enum has a length, and nothing
today makes them agree. A case that reads the number out of the paragraph and
compares it to `len(ElementKind)` holds after the next member is added, which a
literal assertion that the words "Two members" are absent does not.
