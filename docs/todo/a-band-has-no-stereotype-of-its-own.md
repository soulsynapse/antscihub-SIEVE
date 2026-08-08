---
title: A band has no stereotype of its own, and three of detect's params are one
priority: normal
phase: 1
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_detect_tool.py -k the_three_bands_declare -q"
opened: 2026-08-07
---

# A band has no stereotype of its own

`ParamStereotype` closes at five kinds and `SPAN` is written as "a half-open
interval of frames or time". `tools/detect.py` has three parameters that are a
pair of handles dragged along an axis — `freq_band` in Hz, `value_band` in the
incoming signal's units, `count_frac` as a fraction of the frame's elements —
and none of the three is frames or time. They are declared `SPAN` today because
the map is total over `params_model` and the tool had to register; the
declaration says the right thing about *how the value is populated* and the
wrong thing about what axis it is populated on.

Ruled 2026-08-07: a band is its own kind, and the sixth member is what lands.
`SPAN` keeps its narrow meaning — frames or time, and therefore the timeline —
because the stereotype's consumer is a widget *and a handoff surface*, and that
is the whole distinction here. As controls the two are indistinguishable: a
lo/hi pair, two handles, dragged. As surfaces they share nothing, and the
product settled that before the vocabulary existed — VISION's in-pipeline table
carries `Band drag → graphs repaint` at 50 ms as its own row, tighter than the
100 ms it gives scrubbing, so a band drag is already a distinct interaction on a
distinct surface with a distinct ceiling. Declaring `freq_band` as `SPAN` tells
Phase 7's generator to put frequency handles on the scrubber.

The alternative the earlier draft weighed — widening `SPAN` to "an interval on a
declared axis" — is refused, and not on cost. It needs the axis to come from
somewhere, that somewhere is a second declaration, and
`adr/declared-means-verified.md` will not admit one before Phase 7's generator
reads it. It also cannot be honest across these three: `freq_band` is Hz, a
fixed physical unit; `value_band` is in the upstream node's output units, which
are not knowable at spec time; `count_frac` is dimensionless. One axis enum does
not cover a runtime-dependent unit.

So the kind is defined on the pair, not on the plot: an ordered lo/hi on a value
axis rather than the time axis. All three of detect's params are that honestly,
including `count_frac`, which is a pair and so could not have been
`SCALAR_RANGE` either. *Which* plot a band is grabbed on stays undeclared — it
is the same question as
`docs/todo/a-composite-parameter-prints-no-shape-and-no-bounds.md`'s bounds, it
is answerable only against a generator, and it arrives with one.

The vocabulary's docstring says a sixth member is forced by a tool that cannot
be expressed in five and is a deliberate decision rather than a place to put a
tool's own presentation. This is that tool, and the kind is named for the axis
class it populates and not for detection, so the next tool with a threshold pair
pays nothing. Sixth is where it stops being cheap: `adr/gui-knows-kinds-not-tools.md`
is the asymmetry that tools grow fast because kinds grow slowly, and the count
is the only thing keeping the second half true.

The spelling is `BAND = "band"`, which is the word VISION's budget table already
uses for the interaction — the naming is part of the ruling rather than
something the session writing the enum decides, since a stereotype value is an
identity value and `tests/unit/test_tool_id_spelling.py` is what happens to
identity values that get two spellings.

`tools/detect.py` re-registers with the new kind, `SPAN`'s docstring says what
it now excludes, and `core/tool_base.py`'s closed-vocabulary prose says six.
`ToolSpec` refusing an unknown kind by name is still the only consumer, which is
why this is cheap now and is not after a generator reads it.

## The seat is claimed twice, and "sixth" is written in three places

A path stereotype is already settled too, in
[ADR-18](../adr/a-users-file-wires-in-like-any-other-input.md) — "a path param
is a presentation stereotype whose handoff surface is a file or folder picker" —
and it is spent by
[the-first-source-tool-moves-the-three-single-root-assumptions.md](the-first-source-tool-moves-the-three-single-root-assumptions.md),
which argues its own case as *the* sixth member forced by a tool that cannot be
expressed in five. Both rulings stand; what cannot is the arithmetic. This item
is phase 1 and that one is phase 3, so a band lands sixth and a path lands
seventh, and the scarcity sentence each item leans on is spent once rather than
twice.

So the paragraph this item rewrites is the shared one, not the band's own. Three
sites say "sixth" and only the first is prose about a count:

- `ParamStereotype`'s class docstring, "a sixth member is a deliberate decision
  forced by a tool that cannot be expressed in five".
- `ToolSpec.__post_init__`'s refusal message (`core/tool_base.py`), which
  enumerates the members dynamically and then says "and a sixth kind is a
  decision about what the GUI can generate" — the enumeration stays right and
  the ordinal goes wrong the moment this lands.
- [a-run-names-the-external-files-it-needs-before-it-starts.md](a-run-names-the-external-files-it-needs-before-it-starts.md),
  which states "closed at five" as a fact its walk argument rests on.

What lands here is the rule stated without an ordinal in it — the vocabulary is
closed, a new member is a deliberate decision forced by a tool that cannot be
expressed in the existing ones, and the count is `len(ParamStereotype)` — so the
path member costs a member and not a rewrite of the rule. Whether the count is
worth asserting the way
[elementkind-counts-two-members-over-three.md](elementkind-counts-two-members-over-three.md)
asserts its own is that item's shape to reuse, and it is phase 1 and ahead of
this one in the drain.
