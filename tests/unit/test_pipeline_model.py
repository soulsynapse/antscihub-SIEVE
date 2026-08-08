"""Schema v1: what the document must carry, and what it must refuse to.

Each case here stands in for a way the document stops being the thing a run is
reproducible from — one that reads back as something else, one that needs the
tools installed to open, one that lets presentation state in, or one whose node
references have gone stale under an edit.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from sieve.core.pipeline_model import (
    SCHEMA_VERSION,
    CropRecord,
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    Sink,
    SourceRef,
    SourceSpan,
    as_project_path,
    project_path_for,
    resolved_params,
)
from sieve.core.types import ROI


def make_project() -> Project:
    """A project exercising every field, so a round trip can lose one."""
    crop = Node(
        node_id="n1",
        tool_id="crop",
        version="1.0.0",
        params={"region": {"x": 0, "y": 0, "width": 64, "height": 64}},
    )
    threshold = Node(node_id="n2", tool_id="threshold", version="2.1.0", params={"level": 0.25})
    return Project(
        source=SourceRef(path="../footage/arena.MP4"),
        replicates=(
            Replicate(
                name="Replicate 1",
                replicate_id="r1",
                overrides={"n2": {"level": 0.4}},
            ),
            Replicate(
                name="Replicate 2",
                replicate_id="r2",
                overrides={"n1": {"region": {"x": 64, "y": 0, "width": 64, "height": 64}}},
            ),
        ),
        pipeline=Pipeline(
            nodes=(crop, threshold),
            edges=(Edge(upstream="n1", downstream="n2"),),
        ),
        checkpoints=("n1",),
        outputs=(
            Sink(sink_id="s1", node_id="n2", format="csv", path="detections", params={"fps": 30}),
        ),
        crops=(
            CropRecord(
                path="crops/r1.mkv",
                region=ROI(0, 0, 64, 64),
                format="luma",
                span=SourceSpan(start=120, end=420),
                cut_from="sha256:parent",
                decoder="ffmpeg-7.0",
            ),
        ),
    )


class TestRoundTrip:
    def test_yaml_round_trip_preserves_the_document(self, tmp_path: Path) -> None:
        # The load-bearing claim of the whole module: what comes back is what
        # went in. Every field is populated in the fixture so that a field that
        # silently stops serializing fails here rather than at run time, when
        # the symptom is a run that completes and is wrong.
        original = make_project()
        path = tmp_path / "arena.sieve.yaml"
        original.save(path)

        assert Project.load(path) == original

    def test_saving_twice_writes_identical_bytes(self, tmp_path: Path) -> None:
        # Stability, not merely correctness. A project whose YAML churned on
        # every save would make version control useless for the one file a user
        # most wants a history of, and would do it invisibly.
        project = make_project()
        first = tmp_path / "a.sieve.yaml"
        second = tmp_path / "b.sieve.yaml"
        project.save(first)
        Project.load(first).save(second)

        assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")

    def test_relocating_rebases_every_stored_path(self, tmp_path: Path) -> None:
        # Moving a project folder is how footage reaches a cluster. The source,
        # the sink directories and the written crops all have to follow, and a
        # rebase that handled only the source would be found by a run that wrote
        # its outputs into whatever happened to sit beside the new location.
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "nested" / "new"
        project = make_project()

        moved = project.relocated(old_dir, new_dir)

        assert moved.source.resolve(new_dir) == project.source.resolve(old_dir)
        assert moved.outputs[0].resolve(new_dir) == project.outputs[0].resolve(old_dir)
        assert moved.crops[0].resolve(new_dir) == project.crops[0].resolve(old_dir)


class TestIndependenceFromTheRegistry:
    def test_a_project_naming_an_unknown_tool_still_loads(self) -> None:
        # The reason `tool_id` resolution lives in `pipeline/dag.py` and not
        # here. A project that referenced a tool this build lacks must open — so
        # the user can be told *which* tool to install, and so a front end can
        # draw a graph it cannot execute. Registry awareness in this layer would
        # turn that into a parse failure naming nothing.
        text = """
schema_version: 1
source: {path: arena.MP4}
pipeline:
  nodes:
    - {node_id: n1, tool_id: wavelet_bands, version: 2.1.0, params: {bands: 6}}
  edges: []
"""
        project = Project.from_yaml(text)

        assert project.pipeline.node("n1").tool_id == "wavelet_bands"
        assert project.pipeline.node("n1").params == {"bands": 6}

    def test_a_sink_format_that_cannot_survive_a_path_or_a_shell_is_refused(self) -> None:
        # A sink format is resolved by name at run time exactly as `tool_id` is,
        # and lands in file names and CLI arguments on the way, so it carries
        # `tool_id`'s spelling rule rather than a looser one of its own. An enum
        # would be the alternative and would close the writer set.
        with pytest.raises(ValidationError, match="sink format must match"):
            Sink(node_id="n1", format="CSV", path="detections")

    def test_a_node_id_the_filesystem_cannot_hold_is_refused_at_load(self) -> None:
        # A checkpoint is `<node_id>.npy` and the manifest names ids too, so an
        # id carrying a separator aims a write outside the folder it was meant
        # for — and the way to get one is to hand-edit the YAML, which is why
        # the document is refused as it is read rather than by each consumer as
        # it builds a path. Sanitizing instead would mint one mapping per
        # consumer, and two ids sanitizing alike is one file holding two
        # results.
        with pytest.raises(ValidationError, match="node_id must match"):
            Project.from_yaml(
                "source: {path: arena.MP4}\n"
                "pipeline:\n"
                "  nodes: [{node_id: ../escape, tool_id: downsample, version: 1.0.0}]\n"
            )
        with pytest.raises(ValidationError, match="node_id must match"):
            Node(node_id="a/b", tool_id="downsample", version="1.0.0")
        # A *trailing* newline is the one character `$` would let through —
        # Python spells it `(?=\n?\Z)`, not `\Z` — and a quoted scalar is all it
        # takes to write one. It reaches `open_memmap` as a file name: an
        # `OSError` on Windows, and on POSIX a real file whose name breaks the
        # shell quoting this field's docstring says it must not depend on.
        with pytest.raises(ValidationError, match="node_id must match"):
            Node(node_id="abc\n", tool_id="downsample", version="1.0.0")
        with pytest.raises(ValidationError, match="node_id must match"):
            Project.from_yaml(
                "source: {path: arena.MP4}\n"
                "pipeline:\n"
                '  nodes: [{node_id: "abc\\n", tool_id: downsample, version: 1.0.0}]\n'
            )
        # Looser than `tool_id`'s, and it has to be: the generated id is
        # `uuid4().hex`, which begins with a digit more often than not.
        assert Node(node_id="9f2c", tool_id="downsample", version="1.0.0").node_id == "9f2c"

    def test_a_tool_id_that_cannot_key_a_cache_is_refused(self) -> None:
        # Not registry awareness — it never asks whether the tool exists — but
        # the same syntactic contract `ToolSpec` applies. An id that depends on
        # case folding to stay itself is one that stops being itself somewhere
        # between a YAML file, a cache key, and a shell argument.
        with pytest.raises(ValidationError, match="tool_id must match"):
            Node(tool_id="Downsample", version="1.0.0")
        with pytest.raises(ValidationError, match=re.escape("version must be MAJOR.MINOR.PATCH")):
            Node(tool_id="downsample", version="1.0")

    def test_a_tool_id_or_version_ending_in_a_newline_is_refused(self) -> None:
        # `node_id`'s trailing-newline hole, in the two fields that were the
        # precedent for spelling it `$`. Neither becomes a path, so the
        # consequences are not that one: a `tool_id` misses the registry and is
        # named back in a message whose two spellings are indistinguishable on a
        # terminal, and a `version` reaches `SEMVER_PATTERN.match(...).group()`
        # on the cache-key path, where one tool version keys two entries and the
        # reviewer-rerun promise quietly holds a duplicate.
        with pytest.raises(ValidationError, match="tool_id must match"):
            Node(tool_id="downsample\n", version="1.0.0")
        with pytest.raises(ValidationError, match=re.escape("version must be MAJOR.MINOR.PATCH")):
            Node(tool_id="downsample", version="1.0.0\n")
        # A *bare* newline in a quoted scalar folds to a space, so writing one
        # takes the escape — which is what a hand edit is.
        with pytest.raises(ValidationError, match="tool_id must match"):
            Project.from_yaml(
                "source: {path: arena.MP4}\n"
                "pipeline:\n"
                '  nodes: [{node_id: n1, tool_id: "downsample\\n", version: 1.0.0}]\n'
            )
        with pytest.raises(ValidationError, match=re.escape("version must be MAJOR.MINOR.PATCH")):
            Project.from_yaml(
                "source: {path: arena.MP4}\n"
                "pipeline:\n"
                '  nodes: [{node_id: n1, tool_id: downsample, version: "1.0.0\\n"}]\n'
            )


class TestPurity:
    def test_front_end_state_cannot_be_stashed_in_the_document(self) -> None:
        # `extra="forbid"` is what makes the rule cost something to break: a GUI
        # wanting to persist zoom or panel layout has to edit
        # `core/pipeline_model.py` to do it, which is the review the rule exists
        # to force. Without this, an unknown key would round-trip out and the
        # document would quietly stop being the thing two machines agree about.
        with pytest.raises(ValidationError):
            Project.from_yaml("source: {path: arena.MP4}\nzoom: 2.5\n")
        with pytest.raises(ValidationError):
            Project.from_yaml(
                "source: {path: arena.MP4}\n"
                "pipeline:\n"
                "  nodes: [{tool_id: downsample, version: 1.0.0, scroll_x: 40}]\n"
            )

    def test_node_carries_identity_and_nothing_else(self) -> None:
        # The cache-key line, pinned. Everything on `Node` feeds the key, so a
        # field that does not change the node's output must not appear here —
        # `checkpoints`, `outputs` and `crops` live on `Project`, keyed by node
        # id, for exactly this reason. This fails when someone moves one of them
        # onto the node for convenience, because the alternative way to discover
        # it is a cache that misses whenever an output path changes.
        assert set(Node.model_fields) == {"node_id", "tool_id", "version", "params"}

    def test_a_document_from_a_newer_build_is_refused(self) -> None:
        # Refusing beats guessing: a forward-compatible reader that ignored
        # fields it did not understand would run a pipeline that is not the one
        # the document describes, and would report success.
        with pytest.raises(ValidationError, match="schema version"):
            Project.from_yaml(f"schema_version: {SCHEMA_VERSION + 1}\nsource: {{path: a.MP4}}\n")


class TestReferentialIntegrity:
    def test_an_edge_naming_no_node_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="edge names no such node"):
            Pipeline(
                nodes=(Node(node_id="n1", tool_id="downsample", version="1.0.0"),),
                edges=(Edge(upstream="n1", downstream="ghost"),),
            )

    def test_a_sink_naming_no_node_is_refused(self) -> None:
        # A sink is what makes the document runnable, so one pointing at a node
        # that is not there is an output nothing can ever write — discovered by
        # the executor at the end of a run rather than when the document was
        # assembled, which on a cluster is hours later.
        with pytest.raises(ValidationError, match="sink names no such node"):
            Project(
                source=SourceRef(path="arena.MP4"),
                outputs=(Sink(node_id="ghost", format="csv", path="detections"),),
            )

    def test_two_nodes_may_not_share_an_id(self) -> None:
        # `node_id` is what edges, checkpoints, sinks and overrides all
        # reference, so a duplicate makes every one of those ambiguous — and
        # `Pipeline.node` would answer with whichever came first, silently.
        with pytest.raises(ValidationError, match="duplicate node_id"):
            Pipeline(
                nodes=(
                    Node(node_id="n1", tool_id="blur", version="1.0.0"),
                    Node(node_id="n1", tool_id="threshold", version="1.0.0"),
                )
            )

    def test_two_replicates_may_not_share_an_id(self) -> None:
        # `replicate_id` is what downstream artifacts key on, so a duplicate is
        # two arenas whose results cannot be told apart after the fact.
        with pytest.raises(ValidationError, match="duplicate replicate_id"):
            Project(
                source=SourceRef(path="arena.MP4"),
                replicates=(
                    Replicate(name="one", replicate_id="r1"),
                    Replicate(name="two", replicate_id="r1"),
                ),
            )

    def test_a_node_may_not_be_checkpointed_twice(self) -> None:
        # `checkpoints` is a set of node ids wearing a tuple, because the order
        # is not meaningful and a repeat is a document that asks for one write
        # twice.
        node = Node(node_id="n1", tool_id="blur", version="1.0.0")
        with pytest.raises(ValidationError, match="duplicate checkpoint"):
            Project(
                source=SourceRef(path="arena.MP4"),
                pipeline=Pipeline(nodes=(node,)),
                checkpoints=("n1", "n1"),
            )

    def test_two_sinks_may_not_share_an_id(self) -> None:
        # `sink_id` exists so a handoff can toggle one output without rewriting
        # the list positionally, which a duplicate makes impossible: the toggle
        # would hit both or either.
        node = Node(node_id="n1", tool_id="blur", version="1.0.0")
        with pytest.raises(ValidationError, match="duplicate sink_id"):
            Project(
                source=SourceRef(path="arena.MP4"),
                pipeline=Pipeline(nodes=(node,)),
                outputs=(
                    Sink(sink_id="s1", node_id="n1", format="csv", path="a"),
                    Sink(sink_id="s1", node_id="n1", format="mkv", path="b"),
                ),
            )

    def test_two_edges_may_not_feed_one_node(self) -> None:
        # Structural, not registry-aware: whatever the tool turns out to be, its
        # one input carries one stream. A second input is a contract change
        # (`core/tool_base.py` cut the port protocol), not a graph the document
        # should quietly accept and let the executor discover it cannot run.
        nodes = tuple(
            Node(node_id=node_id, tool_id="blur", version="1.0.0") for node_id in ("a", "b", "c")
        )
        with pytest.raises(ValidationError, match="two edges feed"):
            Pipeline(
                nodes=nodes,
                edges=(Edge(upstream="a", downstream="c"), Edge(upstream="b", downstream="c")),
            )

    def test_an_edge_from_a_node_to_itself_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="to itself"):
            Edge(upstream="a", downstream="a")

    def test_replacing_the_graph_catches_stale_checkpoints_and_sinks(self) -> None:
        # The case a constructor-only check misses. `checkpoints`, `outputs` and
        # every replicate's overrides hold node ids, and swapping the pipeline
        # out is precisely the moment those go stale — a checkpoint on a node
        # that no longer exists is a write the executor cannot schedule.
        project = make_project()
        replacement = Pipeline(nodes=(Node(node_id="n9", tool_id="blur", version="1.0.0"),))

        with pytest.raises(ValidationError, match="overrides no such node"):
            project.with_pipeline(replacement)

        following = project.with_param_reset("n2", "r1").with_param_reset("n1", "r2")
        with pytest.raises(ValidationError, match="checkpoint names no such node"):
            following.with_pipeline(replacement)

        # Each of the three is checked separately, so clearing them together
        # would leave the last one named here asserted about only by this case's
        # title.
        without_checkpoints = following.model_copy(update={"checkpoints": ()})
        with pytest.raises(ValidationError, match="sink names no such node"):
            without_checkpoints.with_pipeline(replacement)

        bare = without_checkpoints.model_copy(update={"outputs": ()})
        assert bare.with_pipeline(replacement).pipeline == replacement

    def test_an_override_naming_no_node_is_refused(self) -> None:
        # Same staleness a checkpoint has, and it survives every save
        # otherwise — a deviation nothing reads, waiting for a new node to be
        # handed the dead id.
        with pytest.raises(ValidationError, match="overrides no such node"):
            Project(
                source=SourceRef(path="arena.MP4"),
                replicates=(Replicate(name="one", overrides={"ghost": {"level": 0.5}}),),
            )


class TestLookup:
    def test_a_node_lookup_for_an_absent_id_raises_keyerror(self) -> None:
        # `Pipeline.node` declares the `KeyError` in its docstring and is the
        # route `pipeline/dag.py` resolves an edge endpoint by. Returning `None`
        # instead surfaces as an `AttributeError` several frames downstream,
        # naming an attribute rather than the id that was not there.
        pipeline = make_project().pipeline

        with pytest.raises(KeyError) as absent:
            pipeline.node("ghost")

        assert absent.value.args[0] == "ghost"

    def test_a_node_lookup_for_a_present_id_returns_it(self) -> None:
        pipeline = make_project().pipeline

        assert pipeline.node("n2").tool_id == "threshold"


class TestPerReplicateDeviation:
    def _project(self) -> Project:
        """Two regions and one node carrying two parameters."""
        node = Node(
            node_id="n1", tool_id="threshold", version="1.0.0", params={"level": 0.5, "blur": 3}
        )
        return Project(
            source=SourceRef(path="arena.MP4"),
            replicates=(
                Replicate(name="one", replicate_id="r1"),
                Replicate(name="two", replicate_id="r2"),
            ),
            pipeline=Pipeline(nodes=(node,)),
        )

    def test_untouched_replicates_follow_the_newest_edit(self) -> None:
        # The whole workflow, and the reason for the second write. Configuring
        # arena 1 must leave arena 2 showing arena 1's settings, so twelve
        # arenas are configured once. A `with_param_edit` that stored the
        # override and left `Node.params` alone would pass every other case here
        # and make the user configure all twelve.
        project = self._project().with_param_edit("n1", "r1", {"level": 0.9, "blur": 3})

        assert project.params_for("n1", "r2") == {"level": 0.9, "blur": 3}
        assert project.pipeline.node("n1").params == {"level": 0.9, "blur": 3}

        moved = project.with_param_edit("n1", "r2", {"level": 0.2, "blur": 3})

        # Arena 1 pinned its level and does not follow; arena 2 is now the
        # default anything unconfigured inherits.
        assert moved.params_for("n1", "r1") == {"level": 0.9, "blur": 3}
        assert moved.params_for("n1", "r2") == {"level": 0.2, "blur": 3}

    def test_a_pinned_parameter_does_not_freeze_its_siblings(self) -> None:
        # Sparsity is per key, not per node, and this is what that buys: one dim
        # arena holds its own threshold while still picking up a later change to
        # a blur radius nobody varied. An override that stored the whole
        # submitted parameter set would leave arena 1 on blur 3 forever,
        # silently — the run completes and the arenas are no longer comparable.
        project = self._project().with_param_edit("n1", "r1", {"level": 0.9, "blur": 3})
        project = project.with_param_edit("n1", "r2", {"level": 0.5, "blur": 7})

        assert project.params_for("n1", "r1") == {"level": 0.9, "blur": 7}
        assert project.replicate("r1").overrides == {"n1": {"level": 0.9}}

    def test_no_read_path_hands_out_a_writable_parameter(self) -> None:
        # `frozen=True` is one level deep, and the parameter this item's own
        # mechanism introduced — the crop node's region — is two. Every one of
        # these reads used to alias the mapping inside the model, so a front end
        # holding a parameter form could change what the document hashes to
        # after it had been handed to an executor: a run that completes and is
        # wrong, which is what the module docstring exists to prevent.
        project = make_project()
        node = project.pipeline.node("n1")

        with pytest.raises(TypeError):
            project.params_for("n1")["region"]["y"] = 777
        with pytest.raises(TypeError):
            project.params_for("n1", "r2")["region"]["x"] = 999
        with pytest.raises(TypeError):
            resolved_params(node, project.replicate("r2"))["region"]["x"] = 999
        with pytest.raises(TypeError):
            node.params["region"]["width"] = 1

        assert project == make_project()

    def test_a_list_valued_parameter_is_frozen_too(self) -> None:
        # A band list is the other container a tool's parameters carry, and it
        # is the one the `_Artifact` docstring's `ser_json_inf_nan` case was
        # measured against — so it is stored frozen and stored as a `list`, both
        # because a tuple would come back from YAML as a list and make a saved
        # document unequal to itself.
        banded = Node(
            node_id="n1", tool_id="wavelet_bands", version="1.0.0", params={"cuts": [1, 2]}
        )
        project = Project(source=SourceRef(path="arena.MP4"), pipeline=Pipeline(nodes=(banded,)))

        with pytest.raises(TypeError):
            project.params_for("n1")["cuts"].append(3)

        assert project.pipeline.node("n1").params == {"cuts": [1, 2]}

    def test_resetting_returns_a_replicate_to_the_default(self) -> None:
        # The way back from a pin, and it must not move the default: resetting
        # is not an edit. Without this a parameter set once could only ever be
        # re-pinned, and the replicate would never rejoin what it inherited.
        project = self._project().with_param_edit("n1", "r1", {"level": 0.9})
        project = project.with_param_edit("n1", "r2", {"level": 0.1})

        reset = project.with_param_reset("n1", "r1")

        assert reset.replicate("r1").overrides == {}
        assert (
            reset.params_for("n1", "r1")
            == reset.params_for("n1", "r2")
            == project.params_for("n1", "r2")
        )


class TestCropRecords:
    def _record(self, **changes: object) -> CropRecord:
        base = {
            "path": "crops/r1.mkv",
            "region": ROI(0, 0, 64, 64),
            "format": "luma",
            "span": SourceSpan(start=0, end=100),
            "cut_from": "sha256:parent",
            "decoder": "ffmpeg-7.0",
        }
        return CropRecord.model_validate({**base, **changes})

    def test_a_record_backs_a_cut_by_geometry_and_parentage(self, tmp_path: Path) -> None:
        # The association rule, and the reason it is not a replicate id: a
        # record matched by name would keep serving a box the user has since
        # dragged, which is the one failure that produces wrong pixels rather
        # than a recomputation. Each condition fails in the direction that
        # recomputes.
        (tmp_path / "crops").mkdir()
        (tmp_path / "crops" / "r1.mkv").write_bytes(b"")
        record = self._record()
        region = ROI(0, 0, 64, 64)
        matched = {"source": "sha256:parent", "luma": True, "project_dir": tmp_path}

        assert record.backs(region, **matched)
        assert not record.backs(ROI(1, 0, 64, 64), **matched)
        assert not record.backs(region, source="sha256:reexported", luma=True, project_dir=tmp_path)
        assert not record.backs(region, source="sha256:parent", luma=False, project_dir=tmp_path)
        assert not record.backs(
            region, source="sha256:parent", luma=True, project_dir=tmp_path / "x"
        )

    def test_a_second_write_of_one_cut_replaces_rather_than_accumulates(self) -> None:
        # Two records for one cut are two files claiming to be the same thing,
        # and `backs` would answer yes for both. `with_crop` is the path that
        # cannot produce the pair the document refuses.
        project = Project(source=SourceRef(path="arena.MP4"))
        first = self._record()
        again = self._record(path="crops/r1-retry.mkv")

        recorded = project.with_crop(first).with_crop(again)

        assert recorded.crops == (again,)
        with pytest.raises(ValidationError, match="same cut"):
            recorded.with_crops((first, again))

    def test_a_record_of_a_different_cut_is_kept_beside_it(self) -> None:
        project = Project(source=SourceRef(path="arena.MP4"))
        first = self._record()
        other = self._record(path="crops/r2.mkv", region=ROI(64, 0, 64, 64))

        recorded = project.with_crop(first).with_crop(other)

        assert recorded.crops == (first, other)
        assert recorded.without_crop(first).crops == (other,)


class TestBlankStringsAreRefused:
    """Every stored string here is resolved or matched, and none survives being

    blank: a blank path resolves to the directory holding the project file, so
    it is not a missing value that fails loudly but a valid location that is the
    wrong one. Whitespace counts as blank for the same reason — `" "` resolves
    identically and reads as a real entry in the YAML.
    """

    def test_a_source_path_that_names_no_file_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="source path must not be empty"):
            SourceRef(path="   ")

    def test_a_sink_path_that_names_no_directory_is_refused(self) -> None:
        # A sink writes one output per replicate into the directory it names, so
        # a blank one scatters a fan-out across the project folder itself.
        with pytest.raises(ValidationError, match="sink path must not be empty"):
            Sink(node_id="n1", format="csv", path="")

    def test_a_crop_record_missing_its_path_or_provenance_is_refused(self) -> None:
        # `cut_from` is matched by `backs` and `decoder` is provenance a later
        # question is answered from. A blank either way is a record that claims
        # to know where its pixels came from and does not.
        for field in ("path", "cut_from", "decoder"):
            with pytest.raises(ValidationError, match="crop record fields must not be empty"):
                CropRecord.model_validate(
                    {
                        "path": "crops/r1.mkv",
                        "region": ROI(0, 0, 64, 64),
                        "format": "luma",
                        "span": SourceSpan(start=0, end=100),
                        "cut_from": "sha256:parent",
                        "decoder": "ffmpeg-7.0",
                        field: "",
                    }
                )


class TestConventions:
    def test_the_project_file_sits_beside_its_video(self) -> None:
        # The folder layout: the project names the child folders its derivatives
        # live in, so it belongs at the root of that tree rather than in a
        # user-global application directory. Copying the folder is then how a
        # project reaches another machine.
        video = Path("/data/arena/stab_GX010050.MP4")

        assert project_path_for(video) == Path("/data/arena/stab_GX010050.sieve.yaml")

    def test_a_typed_name_is_coerced_without_with_suffix_eating_the_convention(self) -> None:
        # `with_suffix` replaces the last component, so it would turn
        # `arena.yaml` into `arena.sieve` — the trap this exists to avoid.
        assert as_project_path(Path("/data/arena/arena.yaml")) == Path(
            "/data/arena/arena.sieve.yaml"
        )
        assert as_project_path(Path("/data/arena/arena")) == Path("/data/arena/arena.sieve.yaml")

    def test_a_name_already_obeying_the_convention_is_returned_untouched(self) -> None:
        # Not idempotence for its own sake: the stem of `arena.sieve.yaml` is
        # `arena.sieve`, so coercing twice would produce `arena.sieve.sieve.yaml`
        # and anything that appends to the project name would be keyed off a
        # name nothing forms.
        path = Path("/data/arena/arena.sieve.yaml")

        assert as_project_path(path) == path

    def test_an_empty_span_is_refused(self) -> None:
        # A zero-frame span records a written file covering nothing, which reads
        # back as an artifact that can serve any request and supply no frames.
        with pytest.raises(ValidationError, match="at least one frame"):
            SourceSpan(start=120, end=120)

    def test_a_span_starting_before_the_source_does_is_refused(self) -> None:
        # File frame 0 is source frame `span.start`, and nothing else translates
        # between the two index spaces — so a negative start makes every
        # translation off by that amount rather than failing anywhere.
        with pytest.raises(ValidationError, match="start must be non-negative"):
            SourceSpan(start=-1, end=100)
