---
title: The port refusals and the portless edge have no case
priority: normal
phase: "11"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_tool_contract.py tests/unit/test_dag.py tests/unit/test_offering.py -q -k 'an_absent_port_is_absent_from_the_written_edge or two_edges_feed_one_node_on_two_ports or a_port_declaration_no_edge_could_reach_is_refused or an_edge_naming_a_port_its_tool_has_not_got_is_refused or a_merging_tool_is_not_offered_into_a_gap'"
opened: 2026-08-10
---

# The port refusals and the portless edge have no case

11.2 landed the port-keyed form (`a318b55`) and its criterion reached two
claims: the executor aligns two parents, and crossing two ports moves one key.
Everything the fold authorised *around* those two arrived with no subject at
all. Six refusals and one behaviour change are on the tree and the whole suite
is green with each of them removed.

- `Edge._known_shape_port` refuses a port that is not spelt like a `tool_id`.
- `Edge._without_an_absent_port` is the claim the commit message makes in its
  own last paragraph — a document over a graph with no fan-in is byte-for-byte
  the document it was — and nothing reads a serialized edge to check it. This
  is the one of the seven that is a *schema* claim rather than a refusal, and
  it is the one a later reader will most want pinned, because the argument for
  not bumping `SCHEMA_VERSION` rests on it
  ([the-field-that-names-footage-leaves-the-schema.md](the-field-that-names-footage-leaves-the-schema.md)
  holds that question).
- `ToolSpec._check_ports` refuses three things: a source tool that declares
  ports, a mapping of one port, and a misspelt port name.
- `PortError` is `dag.py`'s whole fourth rejection, both directions of it — an
  edge naming a port on a single-input tool, and an edge naming none into a
  tool that declares several.
- `Pipeline._referential_integrity` refuses two edges into one *port*.
  `test_two_edges_may_not_feed_one_node` covers only the collision on
  `SOLE_PORT`; nothing admits the fan-in that is now legal, so the guard would
  pass unchanged if it had kept refusing by node.
- `offered_tools` skips a tool that declares ports rather than matching one of
  them. That is behaviour, and it is the conservative reading of a question
  [a-second-input-has-no-writer-and-the-box-splices-one-edge.md](a-second-input-has-no-writer-and-the-box-splices-one-edge.md)
  owns — so the case here pins *what it does now*, and that item is free to
  change it.

None of these needs a shipped merge tool. `tests/unit/test_executor.py` already
declares a two-port spec against its own registry, which is the pattern for
every case above.

One thing to repair while here rather than as its own item.
`test_two_edges_may_not_feed_one_node` is named and commented for the posture
11.2 retired — "whatever the tool turns out to be, its one input carries one
stream", citing `core/tool_base.py` as having cut the port protocol. The commit
repaired eight docstrings in `src/` that said the same thing and did not reach
this one, which is a test asserting a rule under a name that now states the
opposite of what the rule is.

## Folded 2026-08-10: the stamp question this item pointed at came back unanswered

The `_without_an_absent_port` bullet above defers the schema half to
[the-field-that-names-footage-leaves-the-schema](the-field-that-names-footage-leaves-the-schema.md),
"holds that question". That item closed on 2026-08-10 answering only its own
half: a *removal* stamps 1, because ADR 38's stamp "rises only when a build
writes into it something the declared version does not have" and a removal
writes nothing new. `test_the_version_a_document_declares_after_the_removal`
pins it.

What it did not answer, and what nothing holds now, is the *addition* half it
had folded in. Under ADR 38 the rise is conditional on content, and nothing in
the tree implements a conditional rise: a project loaded at 1, given a merge,
and saved is stamped 1 and carries a `port` that 1 does not have. The bullet's
own claim — that a document over a graph with no fan-in is byte-for-byte what it
was — is what makes the stamp *true for the portless case* and is exactly the
claim no case reads. So the missing case and the unanswered stamp question are
one subject, which is why this lands here rather than as its own item: pin the
portless edge and what is left is a single question about the one document that
does carry a port.

That question is a ruling and not a case — either `SCHEMA_VERSION` moves to 2
for the addition that already landed, or ADR 38 gains a successor saying a
conditional stamp is not implemented and why that is safe — so a session taking
this item should land the six cases and say in its final message that the ruling
is still Kendrick's rather than answer it in passing.
