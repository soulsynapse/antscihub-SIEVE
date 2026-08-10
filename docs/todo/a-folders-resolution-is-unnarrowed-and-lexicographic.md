---
title: A folder resolves to everything in it in sorted order, and nothing has ruled on either half
status: open
gated_on: nothing
priority: normal
phase: "9"
done_when: 'uv run pytest "tests/gui/test_source_card.py::test_a_folder_holding_a_non_video_lists_what_the_ruling_says" "tests/gui/test_source_card.py::test_numbered_clips_list_in_the_ruled_order" -q'
opened: 2026-08-10
---

# A folder's resolution is unnarrowed and lexicographic, and nothing has ruled

Two questions that were undecidable until a list was drawn on screen, and
`adc0756` drew it. They leave
[the-source-is-a-card-in-the-walk.md](the-source-is-a-card-in-the-walk.md),
which surfaced both and can settle neither, and are one item because they are
one sentence about `core.tool_base.named_files`: it returns every entry in the
folder, in `sorted` order, and both halves are now visible to the user on
`chain_stack.source_note`'s line.

**Narrowing.** A folder holding a README resolves to the README, so the card
lists a file nobody meant as footage. Three places could refuse it and only one
should: the file dialog (`param_form.ask_for_file`, which today narrows by
nothing on the argument that what a tool can read is not something a module
keyed on population kind may know —
[adr/gui-knows-kinds-not-tools.md](../adr/gui-knows-kinds-not-tools.md)), the
tool's own declaration, or nobody, because the reader one step down refuses it
concretely and a guessed pattern would be a second answer to a question already
answered. The last is the current behaviour by omission rather than by ruling.

**Ordering.** `named_files` orders lexicographically and argues for it against
the sequence the directory happened to be written in, which is the right
rejection and not an answer. Lexicographic over unpadded numbering is the
failure a deliberate ordering exists to avoid — `clip_10.mp4` before
`clip_2.mp4`, which for anything that concatenates is a silent wrong answer
rather than a failed run. Whether SIEVE reads the number inside a name or lists
what `sorted` gives and lets the user see it is wrong is the ruling; nothing
reads the ordering as a sequence yet, so today it is wrong-looking rather than
wrong, and the first concatenating tool is where that stops being true.

What the tree pins today, so a session knows what it is changing:
`test_the_source_card_lists_what_its_path_resolved_to` uses `a_first.mp4` and
`b_second.mp4`, which pins the list against reversal and against nothing finer —
lexicographic, directory order and any stable rule agree on that fixture. A case
that can tell them apart is part of this item, not a prerequisite for it.

`done_when` at minting, red because nothing matched:

    $ uv run pytest "tests/gui/test_source_card.py::test_a_folder_holding_a_non_video_lists_what_the_ruling_says" "tests/gui/test_source_card.py::test_numbered_clips_list_in_the_ruled_order" -q
    ERROR: not found: .../test_source_card.py::test_numbered_clips_list_in_the_ruled_order
    (no match in any of [<Module test_source_card.py>])
    no tests ran in 0.13s
    exit: 4

Both test names carry "the ruling" on purpose: either answer is asserted in the
same two places, because the card's list is downstream of wherever the narrowing
and the ordering are decided. A session that lands the ruling renames them to
what it decided.
