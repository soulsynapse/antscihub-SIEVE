# Tool naming: a tool is named for its operation, declares the class it serves, the registry says where the catalogue strains, and the Tab menu groups it by what it derives

Written 2026-11-09 from the naming conversation of that day, on v5 at e17fe0fc; no box ticked.
Amended the same day, still at e17fe0fc, after an architectural review ran its Facts against the
tree: the category derivation is an ordered list with no write group, the csv file carries its kind
on the key line, strain excludes a single type, and hsv keeps its name under the rule it had
contradicted. Read with sieve_player/registry/README.md, which says what a facet is and when one earns a place in
`FACETS`, with the root README's rule that a tool does one thing and a variation is a second tool
beside it, with docs/naming-conventions.md, the five-column view the rule was chosen from, with
docs/naming-generated.md, the table that showed a contract grammar failing in the right places, and
with docs/findings/2026-11-09-tool-report-canaries.md, which recounts the two reports this spec
builds in and what they found. The display pass that computes a node's label from its facets is not
this spec's; it is named under Non-goals.

## Why

The catalogue is named by accretion. `tracks-filter` and `tracks-csv` carry a kind prefix their
blobs twins `filter` and `csv` do not; `threshold` and `inrange` are one operation on two kinds under
unrelated words; `gray`, `hsv`, `mask`, `blobs` and `flow` are tool files named as the wire they
touch, so a reader of the tree opens the wrong one. The session's first answer was a file name that
carries the whole contract, `type-and-type-family-operation-to-type`, and generating it over the
registry (docs/naming-generated.md) showed why not: the facets are already the contract and are
read by the plan, so the name is a lossy second copy that nothing keeps honest, the grammar has no
form for sources, pass-through sinks or `same`, and every spec and finding names tools by their
current words. What the generation did find, in a minute, was four tools refusing a type for no
reason their docstrings give, and that is the shape of thing this spec keeps.

Three decisions follow, each argued against the programs this player copies from. A tool is named
for its operation, Houdini's rule for a SOP, and the name's audience is a reader of the tree; what
a node shows is computed and is the display's. Where one body serves several kinds the tool
declares the class and the name stays bare, dplyr's `filter` over any tibble; where a verb is
shared and the bodies differ, the two are either two operations, which take two words, or one
operation over two units, where the kind is the unit and the prefix says so: filter keeps records
and tracks-filter keeps ids, and ids are tracks' alone, so the prefix is Blender's domain dropdown
written into the name, since a tool here does not widen by a knob. Which of the two a pair is, the
bodies say and the report does not. Pressure tested against the tools the specs say come next, a
tracks smooth, a tracks count, a plane arithmetic, a table reduce, bouts, a density plane, the rule that prefixes at the collision would
rename four existing files as they arrive, because this catalogue's verbs are generic over few
kinds where Houdini's are geometry's own; the class declaration moves none of them.

The reports are the canary. A question about the catalogue is asked of what tools declare, printed
by the registry, gating nothing, before it is ever a rule a tool author must know; the registry's
orphan-type check is the one instance the tree already has. This keeps the thing Kendrick weighs
most, that a tool is made fast and may duplicate another, and moves the pondering to after the
fact, where a report answers it. Nothing here adds a facet, since the registry's own rule admits one
only when something in the player reads it; the one classification the catalogue wants, a category
for the Tab menu, derives from the facets the way the strain does, and so rides this branch rather
than waiting on a feature of its own. That is also what makes a minted verb cheap for the user:
Houdini's and Blender's menus are browsed by group, dplyr's are learnt by heart, and a derived group
puts a new word where it is found without anyone filing it.

## How to read this

Each `##` below is a deliverable: an `Assumes:` line naming what it builds on, a sentence of why,
then done-when assertions, each a box with a `Check:` that is a test in `tests/`. A box is ticked
by a session once its test passes in the tree; a session never unticks or rewrites an assertion,
and before building toward an unticked box checks whether the tree already meets it. Where a
result is worth Kendrick's eye before the next deliverable leans on it, a `Worth a look:` line says
what to look at; it is not a gate. Nothing here says how. Any deliverable whose `Assumes:` are all
done is available; among those the earlier one in the file first. The branch is done when every
box is ticked. Every operation word in this spec is Kendrick's to choose: a box that renames says
what the new name must not be and leaves what it is to him, and a session proposes words in its
report and never writes one into a tool.

Words. A *type* is a string a tool's `EXPECTS` or `PRODUCES` names. A *class* is a set of types
that a body may serve alike; the registry holds the table. A tool *strains* a class when its
declared types name more than one of the class's types and not all of them; a tool naming one type
alone does not strain, a heuristic and not a principle, since inrange's refusal of gray is the one
the finding called arguable and this definition cannot see it. A *verb* is a tool's `NAME` with the type and class
words removed. A *pair* is two tools the registry reports as possibly one tool declared twice.

## The class table and the strain report

Assumes: nothing.

The one declared thing: a table of classes in the registry, and a report line per tool that
strains a class, so a refusal is seen the day it is written and
answered by the tool's author rather than found by a naming exercise.

Facts to weigh, read off the tree at e17fe0fc. `types(entries)` already maps each type to its
producers and expecters and the report prints that first, so the classes sit beside it. The
`--check` fails on a type nothing produces or nothing expects, which is also the typo guard for a
misspelt `EXPECTS`, so no new check is owed for that. The video node is not a tool and is passed
to `types` as `VIDEO`; a class table needs no such extra. docs/findings/2026-11-09-tool-report-canaries.md's
table has the ten strains at this tree and which of them are principled; the report prints the
strain and never the verdict, since the verdict is a reading of the body. The finding's script
strained only tools naming several types, which is why its count is ten and not the thirty a
proper-subset reading gives, and the Words above write that choice down.

- [ ] The registry holds a class table, each class a name and the set of types it covers, with
  `plane` and `table` in it at least, and the report prints, after the types, each tool whose
  declared `EXPECTS` names more than one type of a class and not all of them, with the class and
  the types it lacks, and prints nothing for a tool naming one type alone.
  Check: a test builds entries whose `EXPECTS` is one class whole, a proper subset of it, and a
  single type, and reads the subset alone in the strain lines.
- [ ] `--check` fails on a class whose types are not all types some tool under `tools/` produces
  or expects, so the table cannot name a type the catalogue has left.
  Check: a test runs the check over a root with one tool and a class table naming a type no tool
  there uses and reads the failure.

Worth a look: the strain lines over `tools/` at this tree against the finding's table; which of the
four arbitrary refusals Kendrick lifts is his, and lifting one is a change to that tool with its
own test, not this spec's.

## The pair report

Assumes: The class table and the strain report.

A second report line: two tools sharing a verb, or sharing most of their top-level names, so a
tool written fast beside its twin is seen the next time the registry is read and nobody ponders
before writing it.

Facts to weigh, read off the tree at e17fe0fc. The finding's second script names the two pairs at
this tree with a lexical verb over the kind words and a names-shared fraction with a threshold tuned
on one pair; its docstring says why a source ratio was tried and dropped. The registry imports a
tool to probe it, so the module is at hand and its top-level names need no second read of the
file; the facets in `FACETS` are excluded from the shared set, since every tool has them. A pair
line is a question and prints no verdict: the finding shows one pair is a merge and the other two
operations, and only the bodies say which.

- [ ] The report prints each pair of tools whose verbs are equal once the types and classes of the
  table are removed from `NAME`, and each pair sharing most of their top-level names outside
  `FACETS`, with the fraction, and prints neither for pairs that do not.
  Check: a test over a root with a tool, its kind-prefixed twin sharing its sink functions, and
  a third tool of another verb reads the one pair with its fraction and no other.

## One csv

Assumes: The pair report.

csv and tracks-csv share tools/_csvfile.py's key line, write and widget and the sink's quartet,
and differ in whether a row writes one value or one line per record; that is the wire's shape, so
one tool over signal and the table types writes both, and blobs, which tracks-csv's column rule
already strips of `id` and `contour`, fall out of it with one more clause to that rule. What the
merge removes is the file's declaration of its kind, which today is the name of the tool that wrote
it; the key line takes that over, since a filename is the user's to change and the key line is not.

Facts to weigh, read off the tree at e17fe0fc. tools/tracks_csv.py's `fields` drops `contour` and
`id` and any object column, and `columns` puts `id` after `time`; a blobs table has no `id`, so its
line wants the `id` column absent rather than blank, which is a second column rule and not a second
tool. A blobs table from region carries `name`, a unicode column that is neither object nor
numeric, and `fields` keeps it today, so the rule's third clause drops any column that is not
numeric; the Check's blobs series carries such a column. tools/csv.py writes `row`, `time`,
`signal`, `gate` and its `count` is the signal's length; tracks-csv's `count` is the rows', and its
trace and band are the records per row, as its docstring says: the merged tool's trace over a table
wire is that count, a statistic the tool mints, and its docstring says so. Both `default_name`s put
the row range in the stem and tracks-csv adds `_tracks`; the suffix stays as the default and is not
where the kind lives, since the Write dialog takes any name. tools/_csvfile.py's `key_line` already
appends an optional `plate=first:increment`, and a `kind=` field sits beside it the same way; a
file without one, written before this branch, reads as kind unknown. `PRODUCES` is `"signal"` on
one and `"tracks"` on the other, and a pass-through is `"same"`, which the registry already means.
tools/_csvfile.py's docstring names both tools, and tests/test_seams.py holds that a tool imports
only `_` modules under tools/ and never another tool. tools/resolve.py reads tracks-csv's file back
through `_csvfile.read` and `tables_of`, which drops row, time and gate, casts `id` to int32 and
every other column to float64, and raises KeyError on a header without `id`; the tracks line's shape
is what that reader finds, and a signal or blobs csv handed to it today fails by KeyError, which
the kind on the key line turns into a sentence. tests/test_resolve.py's read-back test calls
`tracks_csv.write` by name, so it is rewritten against the merged tool and is then the one test
pinning the header shape resolve reads. Documents store `NAME`, so a saved document naming
tracks-csv stops loading; the gitignored purb documents in video-tests are rewritten by hand and no
alias table is owed before alpha.

- [ ] One tool writes a csv from a signal, a blobs series or a tracks series, pass-through, with
  the per-row line for a signal, the per-record line with `id` for tracks and without it for
  blobs, no non-numeric column on either, the key line carrying `kind=` as the type written,
  and tracks-csv is no longer a tool under `tools/`.
  Check: a test writes a two-row signal, a blobs series with a string column and a tracks series
  through the tool and reads back the three kinds on the key lines, the three column headers and
  the line counts; a test reads the registry over `tools/` and finds no tool named tracks-csv.
- [ ] `_csvfile.read` answers the kind, unknown for a file without one, and resolve refuses a
  file whose kind is not tracks with a sentence naming the kind it found, and reads a file of
  unknown kind as it does today.
  Check: tests/test_resolve.py's read-back, moved to the merged tool, still passes; a test hands
  resolve a signal csv the tool wrote and reads the sentence, and a file whose key line has no
  kind and reads it as before.
- [ ] tools/_csvfile.py's docstring, the root README and every spec and finding that names
  tracks-csv as a tool say what is now so, or say it was so at the tree they were written against.
  Check: `rg tracks-csv` over docs/ and README.md finds only lines that date the name.

## Count and size over tracks

Assumes: The class table and the strain report.

count's fold is a table's length and size's method reads any numeric column of a row's table, so
both serve a tracks series, size unchanged and count with its `run` taught to read tables;
declaring it closes two strains the table would otherwise print and is the pattern the Why names,
the class declared and the name left bare.

Facts to weigh, read off the tree at e17fe0fc. tools/count.py folds each row to its length and
tools/size.py iterates `series.data` reading `t.dtype.names`; a tracks table carries blobs'
columns and `id`. The walk folds only a frame node's rows: a series node reading another series
node receives what `sieve_player.graph.gated` fed, the rows as tables, and no fold. A tracks series
comes from track, a series node, so count's `run`, which casts `series.data` to float64, raises
over it today (run at this tree: `ValueError: setting an array element with a sequence`) while
size's, which iterates tables, answers. The body change is count reading a table's length where
`run` meets tables. The tools' docstrings say blobs in. tests/test_count.py and tests/test_size.py
hold the blobs case; the tracks case extends them.

- [ ] count and size declare `EXPECTS` over the table types and compute the same numbers over a
  tracks series as over the blobs series it was tracked from, and their docstrings say so.
  Check: a test runs each over a blobs series and the tracks series track produces from it and
  compares the two signals row for row.

## Tools no longer named for a wire

Assumes: The pair report.

`gray` and `mask` are tool files whose names are a type they do not alone produce, so the tree
reads them as wires; Houdini writes a conversion as `a-to-b` and an application as the verb. The
rule below is the one the report can check, a type's bare name belongs to its one producer, and it
decides the rest: hsv is the one producer of hsv and keeps its name as flow does, though the spec's
first draft renamed it; blobs is produced by region too, so blobs prints in the report until the
line is answered or accepted. The distinction the first draft reached for, a conversion between
representations of one plane against the minting of a new kind, is a reading of bodies the report
cannot see, and a rule the report cannot see is the kind this spec says drifts.

Facts to weigh, read off the tree at e17fe0fc. tools/gray.py and tools/hsv.py are bgr in; tools/mask.py
applies a mask on `mask` to any plane. tools/blobs.py reads gray or mask and tools/flow.py gray or
mask. gray is also produced by bg-subtract, motion, changeenergy, agreement and speed; mask by
threshold, inrange, morphology, combine and blobs-to-mask; blobs by region; hsv by hsv alone and
flow by flow alone. The words are Kendrick's; `bgr-to-gray` and `mask-apply` are the session's
proposals. Module files take underscores where `NAME` takes hyphens, as tracks_filter already does.

- [ ] The report prints each tool whose `NAME` is a type it does not alone produce, and prints it
  for neither gray nor mask once they are renamed, for hsv and flow at all, and for blobs while
  region produces blobs; the root README's A tool section states the rule: a tool is named for
  its operation, declares the class it serves where one body serves it, carries the kind where
  the kind is the unit it works over, takes a second word where the operation differs, and
  carries a type's bare name only as that type's one producer.
  Check: a test over a root with a tool named for a type it alone produces, one named for a type
  another tool produces, and one named for its operation reads the second alone in the report;
  a test over `tools/` reads blobs in the report and neither hsv nor flow.

## The catalogue derives its categories

Assumes: The class table and the strain report.

The family the naming script assigned by hand is nearly all the contract's shape, read as an
ordered list where the first rule that fits decides, so no tool fits two: a source has no
`EXPECTS`; a cache has the `bake` facet; a measure produces signal and does not expect it; a
relate has an `INPUTS` entry and produces `same` or a type among what it expects, which puts
attach, inside, sample, decode, mask, crop, bg-subtract and combine in one group, two wires in and
the first shaped by the second; a convert produces a type not among what it expects; a transform
is the rest, `same` or a type among what it expects with no second input. The order matters:
every measure is a convert by shape, and bake is a transform by shape, so measure and cache are
read before the rules they would otherwise fall into. The first draft had a write group, a
pass-through with a writer, and it is gone: `write` is a module name tools/_csvfile.py reads and
not a facet, and the registry's rule is that a facet exists when the player reads it, so a group
derived from `write` would be a declaration no README states. csv files as a transform, which to
the graph it is, until a second sink family shows what a sink declares. So the category is derived
in the registry as the strain is, a report line before it is a declaration, and the Tab menu
reads it; a tool lands in a group the day it is written and nobody files it. Where the derivation
and a tool disagree, the disagreement is the report's to show and a hand-set facet is the
override, minted when the first such tool exists; the two disagreements known at this tree are
region, a source to the hand table and a convert to the derivation since it expects a plane, and
resolve, a transfer to the table and a transform to the derivation since a path input is not an
`INPUTS` entry. Both derived answers are kept.

Facts to weigh, read off the tree at e17fe0fc. sieve_player/canvas.py's TabMenu is Houdini's Tab
menu as a flat filter line over `menu_entries()`, a substring match on `NAME`, with an unimportable
tool greyed and its error on hover; with a wire pending, `_joins` already narrows the entries to
the tools the wire's type may feed or be fed by, and `_splices` to those a pulled wire may take, so
the compatibility filter exists and this deliverable adds grouping and a description to it. A
tool's docstring opens with its contract in one sentence, "Frame tool: ..." or "Series tool: ...",
which is the description at hand. Houdini's Tab menu nests by category and TouchDesigner's OP
Create dialog shows a column per family; Blender's Shift+A groups by category with a search line
that flattens the groups on typing. The derived categories' names are the session's proposals and
Kendrick's to change; the registry's `CLASSES` and the derivation are the one place they live.
The menu is built for a user's fluency, as polished as the session can make it, with Houdini's Tab
menu, Blender's Shift+A and TouchDesigner's OP Create as the models for what fluent feels like:
the typed text matches across group and name and description, the first match is chosen on Enter,
the groups read in the order a pipeline is built, source first and measure last, and a description is short
enough to read at a glance. The look, the order, the row's layout and how a description shows are
then expected to move with Kendrick's feedback through the branch and after; the boxes below assert
what the menu offers and never where or how, so the polish is free to move without unticking one.

- [ ] The registry derives a category per tool from its facets by the ordered list above, prints
  it in the report beside the tool, and prints a line for each tool whose facets fit no rule.
  Check: a test over entries shaped as a source, a cache, a measure, a relate, a convert and a
  transform reads each category, reads measure for an entry that is a measure and a convert by
  shape and cache for one that is a cache and a transform by shape, and an entry fitting none
  reads in the line; a test over `tools/` reads bake as a cache and csv as a transform.
- [ ] The Tab menu offers every entry under its category, with the first sentence of the tool's
  docstring as its description, the categories flattening to the matches as text is typed, and
  the pending-wire narrowing of `_joins` and `_splices` as it is.
  Check: a test builds the menu over a catalogue of two categories and reads the two groups, each
  entry's description, and the single group left on typing one entry's name.

Worth a look: the menu on the purb document with a wire pulled off a gray node; what reads wrong
in the grouping or the description is this spec's to carry as an Open item and the look is
Kendrick's to change without one.

## Non-goals

- A family facet set by hand on a tool. The category derives, above; a declared facet is the
  override for a tool the derivation gets wrong and is minted when the first exists, under the
  registry's rule that a facet is read by something. csv filed as a transform is not that tool:
  the derivation is right about what csv is to the graph, and a write group waits on a second
  sink family.
- A label computed from the facets in any of naming-conventions.md's five styles. The display
  pass is its own spec; the plan already holds what it needs.
- An alias table from old names to new in the document loader. Pre-alpha, saved documents are
  rewritten; the first release that must load an older document mints it.
- Recipes and group nodes. A recipe is a saved document fragment inserted by paste when wanted;
  a group node is minted when a user asks to collapse one.

## Open

- Whether tracks-filter keeps its prefix or takes a word of its own. The prefix is honest by the
  Why's unit reading, ids being tracks' alone, and the pair report lists the two filters either
  way until it has a way to hear an answer. A word of its own, SLEAP's cull say, is a minted verb;
  Houdini mints freely (Facet, Fuse, PolyBevel) and is browsed by category, dplyr mints almost
  none and is learnt by heart. With the catalogue grouped by derived category on this branch the
  player is the first kind, a verb lands where it is found, and what a synonym still slips past is
  the pair report's lexical verb check and a search by a word the user does not know. Kendrick's
  call, and the spec is written so either keeps every box.
- Whether threshold and inrange are one operation over gray and hsv with a range per channel, so
  that the pair closes as One csv does, or two bodies. A reading of both, and a finding if the
  merge changes a mask on the purb document by a pixel.
- Whether bg-subtract's refusal of mask is a refusal or an omission; the finding's table calls it
  arguable.
- Whether a report line that persists unanswered across several sessions should be sayable as
  accepted, so the strain report does not list motion's single-channel refusal forever. The cost
  is a declaration on the tool; the gain is a report whose every line is live.
- The names-shared threshold of the pair report, tuned on one pair at this tree.
- The blobs line in the wire-name report, live while region produces blobs. Answering it is a
  word for blobs or for region's output, Kendrick's; accepting it is the fourth Open item's
  mechanism, if one is minted.
- Whether a csv of unknown kind, written before the key line carried one, should go on reading
  into resolve forever, or the first release that must not accept one dates the leniency.
