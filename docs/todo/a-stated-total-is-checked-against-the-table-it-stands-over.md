---
priority: low
phase: 0
status: open
gated_on: nothing
opened: 2026-08-07
title: A stated total is checked against the table it stands over
---

# A stated total is checked against the table it stands over

A re-derivation item states how many v2 cases there were and then carries a
table with one row per case. Both numbers have now been wrong in the same
document: 03.3 inherited "33 cases in 15 classes" over a file with 8 classes,
and then wrote "seven v3 cases with no v2 row" over an enumeration of eight
(`findings/loop/2026.08.07-the-run-that-corrected-an-inherited-miscount-wrote-its-own.md`).
The table's own verdict columns were exact in both runs, because a column is
something a grep reaches and a sentence is not.

So: `scripts/doc_index.py` parses a todo item's markdown table, counts its
rows, and fails when a total stated in the item's prose disagrees with it.
The narrow version — a `case_count:` field in the frontmatter checked against
the row count — is probably the whole of it, and is cheaper than parsing English
for numbers. Deciding which is part of the item.

Low rather than a decimal step because nothing downstream reads these totals;
what they cost is a reviewer's time re-doing the arithmetic, and 03.4 and 03.5
each carry a table that will need it.

03.6 is the third instance and the first where the sentence claimed to have
*checked*: "13 and 8 … which are the counts the item states and the counts the
two files have", over v3 files holding 13 and 7. The two readings — v2's counts,
which is what PLAN.md means, and the v3 files the paths name — differ by one, and
the run wrote the clause that asserts they do not. That is the argument for the
frontmatter field over parsing English: a `case_count:` checked against the row
count would also have had nothing to say here, because the wrong number is the
*v3* total, which no row count reaches. Whatever this item builds has to reach
the count the criterion reports, not only the table's height.
