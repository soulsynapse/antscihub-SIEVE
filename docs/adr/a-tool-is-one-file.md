---
title: A new tool is one file
adr: 7
position: "01.03"
status: settled
decided: 2026-08-06
amended: 2026-08-07
---

A tool's machinery is one module in `sieve.tools`; it adds only files it alone
opens and edits none another tool edits, the sole exception being extending a
closed vocabulary that cannot express it.

That exception is argued against the vocabulary's existing members by name. A
tool that has to take a row in a shared list is an architecture failure to stop
and fix, not route around.

Why the line moved from "one file" to "no shared file": the first reading has
been false since the first tool, and the second has held for every one of them
([findings/2026.08.07-every-tool-landed-in-one-src-file-and-none-took-a-row.md](../findings/2026.08.07-every-tool-landed-in-one-src-file-and-none-took-a-row.md)).
`gui/filter_tab.py` is still the counterexample this exists for, and its size
was not the disease: every v2 step had to enter that one file to be usable, so
it accreted eleven jobs and each arrival paid for all the arrivals before it. A
golden array only its own test loads costs nothing anyone else can feel.

The discriminator is what an edit does to the file's future. A vocabulary
converges: mint one kind and the next tool needing it pays nothing, which is
[gui-knows-kinds-not-tools](gui-knows-kinds-not-tools.md)'s asymmetry stated as
a cost curve. A list is linear in tools forever, which is `filter_tab.py`
again in a smaller box. Where a shared artifact genuinely has to exist,
`docs/SCAFFOLD.md` is the available shape — every module in the repo, edited by
nobody, derived by `scripts/doc_index.py` from each module's own docstring.

The exception is bounded because the accommodating things are enumerable, and
they are `core`'s closed vocabularies — `ParamStereotype`, `Mode`,
`StreamKind`, `ElementKind`, `ElementRelation`, `ChannelSpec` — plus the window
contract's shape and the dependency list, since SIEVE not providing a package
is not something a tool can route around. The GUI's handoff surfaces join that
list when there is a GUI to hold them and not before, which is
[declared-means-verified](declared-means-verified.md) applied to this ADR
rather than an exception to it. `core` membership being frozen
([core-membership-is-closed](core-membership-is-closed.md)) is what keeps the
surface from growing quietly.

It is an *iff*, and the burden runs against the tool. "No existing member
expresses this" is a claim its author has every incentive to make — the named
erosion point is that a bespoke two-hour job beats a two-day kind — so the
claim is argued member by member and reviewed as a decision, not taken as a
tool-local convenience. `SPAN` refused by name for a value-axis band is the
worked example (`docs/todo/a-band-has-no-stereotype-of-its-own.md`). The
extension lands in the same commit as the tool that forced it: a vocabulary
member with no tool declaring it is a declaration awaiting a consumer.

Two shapes this rules on directly. A tool with two inputs, which schema v1 has
no contract shape to express, is the licensed case — the port-keyed window is
the extension, so the contract and the tool are one item rather than two
waiting on each other. A shared test table with a row per tool is not: nothing
is missing from SIEVE when a tool's declarations need checking, so the check is
generic over `discover()` or it is a manifest.

One current exception is neither vocabulary nor list. The spelling gate's
foreign-vocabulary waivers grow per borrowed word rather than per tool, and are
a claim about prose rather than a capability; they are exempt as waivers and
that exemption does not generalize.
