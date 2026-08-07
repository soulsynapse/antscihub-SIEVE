---
title: The three templates forbid the quoting they recommend in the same paragraph
priority: high
status: awaiting-review
phase: "00"
gated_on: nothing
done_when: "uv run pytest \"tests/docs/test_doc_index.py::test_the_templates_do_not_forbid_the_quoting_they_recommend\" -q"
opened: 2026-08-07
---

# The three templates forbid the quoting they recommend in the same paragraph

`6862d4d` added the leading-backtick rule to all three `_TEMPLATE.md` files and
extended it to quotes. The extension is false as stated. YAML reserves ``` ` ```,
`"` and `'` at the head of a **plain** scalar; a scalar that opens with a quote
*and closes with it* is the ordinary quoted form and parses:

| written | `yaml.safe_load` |
|---|---|
| ``title: `x` y`` | ScannerError |
| `title: "core"'s membership` | ScannerError |
| `title: "core is closed"` | parses |
| `title: 'a b'` | parses |

So `docs/todo/_TEMPLATE.md`'s "A value may not *open* with a backtick or a
quote … Quote the whole scalar or lead with a word" forbids its own remedy two
sentences later, and forbids the `done_when:` sitting nine lines below it in
the same file. `docs/findings/_TEMPLATE.md` says "An opening quote is reserved
the same way, for the same reason" directly after offering
``probe: "`set(POS_FRAMES)` on 500 frames"`` as the fix.
`docs/adr/_TEMPLATE.md` is the one that escapes: "an **unquoted** one" carries
the qualifier the other two dropped.

What each of them means is the plain-scalar rule, and saying that is the whole
repair — "a value that is not quoted may not begin with a backtick or a quote;
quote the whole thing, or lead with a word." The worker's note records the
extension as deliberate ("all three say backtick *or quote*"), so this is a
wrong rule rather than a slip of phrasing, and it is in the file an author is
reading while writing the field.

`done_when` checks the constructions rather than the wording, so a rewrite that
gets it right passes however it is worded: for each `_TEMPLATE.md`, every
`key: value` example the file presents as legal must parse and every one it
presents as illegal must not, and no sentence forbidding an opening quote may
stand without restricting itself to an unquoted value. Red today on the todo
and findings templates.
