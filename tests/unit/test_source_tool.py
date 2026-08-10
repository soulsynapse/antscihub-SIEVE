"""The first source tool, and the single-root assumptions it moves.

`adr/a-users-file-wires-in-like-any-other-input.md` settles that a picked file
enters as a node with no upstream keying from its own file. Three sites assumed
there was one such node and that the reader fed it, and each is checked here
against a run rather than against a declaration:

- **A graph can have two roots.** It orders, it executes, and the two answer for
  the same frames from different files. A graph with one root passes every
  arithmetic in the system whether or not the second is reachable at all, which
  is why the case is a run and not an assertion about `Dag.order`.
- **A source tool keys from its file.** Swapping the picture underneath a
  pattern that did not move has to move that node's key and nothing else's.
  Getting this wrong is the failure the ADR names outright: the store serves the
  first background's results under the second's name — well-formed key,
  plausible frame, no symptom.
- **The resolution policy stays out of the key and refuses rather than
  ordering.** A pattern naming several files has no answer the filesystem's
  listing order gets to supply, and one naming none is a run that cannot happen.
- **A folder is the case where several is the answer.** The refusal above is
  about a pattern standing in for one file; a param that names a folder names
  everything in it, and the order is the project's rather than the
  filesystem's (`todo/a-source-param-names-a-folder-and-several-files-are-an-ordering.md`).

The fourth case is about the declaration rather than the run, and is here
because it is the one claim a run cannot make: an `emits` that left either
tuple empty would pass against every `accepts` on the shelf, so every graph
containing this node would run with `dag.py`'s edge check switched off — and
each of those graphs would run correctly right up until one of them did not.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from sieve.core.pipeline_model import Node, Pipeline, SourceSpan
from sieve.core.tool_base import ArraySpec, SourceFileError
from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.pipeline.resolve_source import picked_identities, source_files
from sieve.tools import discover
from sieve.tools.footage import SOURCE as FOOTAGE
from sieve.tools.footage import FootageParams
from sieve.tools.pick import SOURCE as PICKED
from sieve.tools.pick import PickParams

PICK = "background"
DOWN = "shrunk"
SOURCE = "footage|1|2"

#: Large enough that `downsample` leaves something of the reader's frame, and
#: the same extent for the picture so a mistaken swap of the two would still be
#: a shape the graph accepts — the assertions are about pixels, not shapes.
WIDTH = HEIGHT = 64

#: What the picker's pattern matches. A general-case match rather than one name,
#: which is the form VISION's scenario states (`*_bg.png`) and the form the
#: refusals below are about.
PATTERN = "*_bg.png"

SPAN = SourceSpan(start=0, end=3)


class ListSource:
    """The run's footage: frame `n` is a field of intensity `n`.

    A list rather than a decoder because what several of these cases turn on is
    which file a node's pixels came from, and a constant per frame is what makes
    that readable off the array.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        data = np.full((HEIGHT, WIDTH), int(index), dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


class RefusingSource:
    """A reader that fails if it is touched at all."""

    def read(self, index: int) -> Frame:
        raise AssertionError(f"decoded frame {index} for a graph whose roots read their own files")


def write_picture(path: Path, fill: int, *, width: int = WIDTH) -> Path:
    """A single-channel picture of one value, at `path`.

    `width` varies so a second write to one path is a different file by size as
    well as by content — `source_identity` reads size and mtime, and a test that
    turned on mtime alone would be turning on the filesystem's clock resolution.
    """
    cv2.imwrite(str(path), np.full((HEIGHT, width), fill, dtype=np.uint8))
    return path


def two_roots(directory: Path) -> Pipeline:
    """A picker and a downsample, side by side, feeding nothing and each other.

    The shape the three single-root assumptions were written against: two nodes
    with no upstream, one of which the reader feeds and one of which opens its
    own file.
    """
    return Pipeline(
        nodes=(
            Node(
                node_id=PICK,
                tool_id="pick",
                version="1.0.0",
                params={"pattern": str(directory / PATTERN)},
            ),
            Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
        ),
        edges=(),
    )


def plan_for(directory: Path) -> ExecutionPlan:
    """The plan for `two_roots`, keyed on whatever the pattern resolves to now."""
    discover()
    dag = Dag.build(two_roots(directory))
    return ExecutionPlan.build(
        dag,
        source=SOURCE,
        span=SPAN,
        picked=picked_identities(source_files(dag, _params(dag))),
    )


def _params(dag: Dag) -> dict[str, object]:
    """Resolved params without a plan, since a plan is what needs them.

    `ExecutionPlan.build` derives the same map; `source_files` is handed that
    one in production. Here it would be a plan built to build a plan.
    """
    return {
        node.node_id: dag.specs[node.node_id].params_model.model_validate(node.params)
        for node in dag.order
    }


class TestTwoRootsAreOneGraph:
    def test_two_roots_order_and_execute(self, tmp_path: Path) -> None:
        """Both roots answer for every frame, each out of its own file.

        The pixels are what separates this from a graph that merely ordered: the
        picker's output is the picture at every frame and the downsample's is the
        reader's frame at that index, so a run that fed the picker from the
        reader — the binding this tool replaces rather than shares — hands back
        `index` where 200 is asserted, on every frame including the first.
        """
        write_picture(tmp_path / "plate_bg.png", 200)
        plan = plan_for(tmp_path)
        reader = ListSource()

        results = list(execute(plan, reader))

        assert [node.node_id for node in plan.dag.order] == [PICK, DOWN]
        assert [node.node_id for node in plan.dag.source_roots] == [PICK]
        assert [int(result.index) for result in results] == [0, 1, 2]
        for result in results:
            assert np.array_equal(
                result[PICK].data, np.full((HEIGHT, WIDTH), 200, dtype=np.uint8)
            ), f"frame {result.index} did not come from the picked file"
            assert np.array_equal(
                result[DOWN].data,
                np.full((HEIGHT // 2, WIDTH // 2), int(result.index), dtype=np.uint8),
            )
        assert reader.reads == [0, 1, 2], (
            "the footage is read once per frame, for the root it feeds"
        )

    def test_a_graph_of_source_roots_alone_never_opens_the_footage(self, tmp_path: Path) -> None:
        """The reader is not touched on a source tool's account.

        The other half of the binding claim, and the half that is invisible in
        the case above — a picker fed from the reader and ignoring what it was
        handed produces exactly the right pixels there. Here there is no footage
        to be handed, which is the project VISION describes: one whose own video
        is not the subject of the graph.
        """
        write_picture(tmp_path / "plate_bg.png", 200)
        discover()
        dag = Dag.build(
            Pipeline(
                nodes=(
                    Node(
                        node_id=PICK,
                        tool_id="pick",
                        version="1.0.0",
                        params={"pattern": str(tmp_path / PATTERN)},
                    ),
                ),
                edges=(),
            )
        )
        plan = ExecutionPlan.build(
            dag, source=SOURCE, span=SPAN, picked=picked_identities(source_files(dag, _params(dag)))
        )

        results = list(execute(plan, RefusingSource()))

        assert len(results) == 3
        assert all(result.source is None for result in results)


class TestASourceToolKeysFromItsFile:
    def test_swapping_the_picked_file_moves_only_its_own_key(self, tmp_path: Path) -> None:
        """The picture moves underneath a pattern that did not.

        Nothing in the document changes between the two plans — same pattern,
        same node, same tool — so a key derived from the graph is identical
        across the swap, which is precisely the invisibility the ADR names. What
        must move is the picker's key alone: the other root reads the footage,
        which did not change, and a run that re-keyed it would recompute a
        whole branch for a file it never opened.
        """
        picture = tmp_path / "plate_bg.png"
        write_picture(picture, 200)
        before = plan_for(tmp_path)

        write_picture(picture, 40, width=WIDTH + 2)
        after = plan_for(tmp_path)

        assert before.dag.pipeline == after.dag.pipeline, "the document is the same document"
        assert before.keys[PICK] != after.keys[PICK]
        assert before.keys[DOWN] == after.keys[DOWN]

    def test_a_source_root_with_no_resolved_file_is_left_unkeyed(self, tmp_path: Path) -> None:
        """No identity, no key — rather than a key over the pattern.

        `picked` is optional because a plan is derivable where nothing is
        mounted, and the failure that reading a pattern instead would produce is
        two different files keying alike. Absent is the same answer
        `NotCacheableError` gives, and it costs the node its cache entry and
        nothing else.
        """
        write_picture(tmp_path / "plate_bg.png", 200)
        discover()
        dag = Dag.build(two_roots(tmp_path))

        plan = ExecutionPlan.build(dag, source=SOURCE, span=SPAN)

        assert PICK not in plan.keys
        assert DOWN in plan.keys


class TestThePatternResolvesToOneFileOrRefuses:
    def test_a_pattern_matching_several_files_is_refused(self, tmp_path: Path) -> None:
        """Two matches are not an order to choose from.

        "The first match" is the filesystem's answer and not the project's, and
        the cost of taking it is a run whose background is whichever name sorted
        first on the machine it ran on. The refusal names both files, because the
        user's next action is to narrow the pattern and they cannot do that
        without knowing what it caught.
        """
        write_picture(tmp_path / "monday_bg.png", 200)
        write_picture(tmp_path / "tuesday_bg.png", 40)
        discover()
        dag = Dag.build(two_roots(tmp_path))

        with pytest.raises(SourceFileError) as refused:
            source_files(dag, _params(dag))

        assert "monday_bg.png" in str(refused.value)
        assert "tuesday_bg.png" in str(refused.value)

    def test_a_pattern_matching_nothing_is_a_run_that_cannot_happen(self, tmp_path: Path) -> None:
        """The other half of the same policy, and the one a default reaches.

        A picker with nothing chosen is a legal document — VISION's new project
        opens on one — so the refusal belongs to the run rather than to the
        parse, and it names the pattern that found nothing.
        """
        discover()
        dag = Dag.build(two_roots(tmp_path))

        with pytest.raises(SourceFileError) as refused:
            source_files(dag, _params(dag))

        assert PATTERN in str(refused.value)


class TestAFolderIsAnOrderingRatherThanAnAmbiguity:
    def test_a_source_param_naming_a_folder_resolves_to_every_file_in_order(
        self, tmp_path: Path
    ) -> None:
        """The distinction, both halves of it, and what a one-file reader does with it.

        A pattern standing in for one file that catches two is an ambiguity —
        the user narrows it, and no order the filesystem supplies is the
        project's answer. A param that names a folder is not that: the answer is
        everything in it, and the question is what order. Lexicographic, so the
        answer is the names the user gave their exports and not the sequence a
        directory happened to be written in.

        The third assertion is where the ordering stops today. `read` hands over
        one file's frames, so a step reading a folder of two refuses — and it
        refuses on its own terms rather than on the pattern's, which is the
        distinction read from the other end.
        """
        write_picture(tmp_path / "b_second_bg.png", 10)
        write_picture(tmp_path / "a_first_bg.png", 20)
        discover()

        found = PICKED.files(PickParams(pattern=str(tmp_path)))

        assert [path.name for path in found] == ["a_first_bg.png", "b_second_bg.png"]
        assert [path.name for path in FOOTAGE.files(FootageParams(path=str(tmp_path)))] == [
            "a_first_bg.png",
            "b_second_bg.png",
        ], "one rule, and both source tools read it"

        with pytest.raises(SourceFileError) as ambiguous:
            PICKED.files(PickParams(pattern=str(tmp_path / PATTERN)))
        assert "narrow" in str(ambiguous.value)

        with pytest.raises(SourceFileError) as unordered:
            PICKED.file(PickParams(pattern=str(tmp_path)))
        assert "narrow" not in str(unordered.value)

    def test_an_unset_param_is_not_the_folder_the_process_happens_to_be_in(self) -> None:
        """`Path("")` is a directory, and a document with nothing chosen is not.

        The folder branch is a `is_dir` test, and the empty string passes it —
        so a source nobody has picked a file for would resolve to whatever the
        process was launched in, which is a run over files the project never
        named rather than the refusal VISION's new project is owed.
        """
        discover()

        with pytest.raises(SourceFileError) as unchosen:
            PICKED.files(PickParams())

        assert "names no file" in str(unchosen.value)


class TestThePickerDeclaresWhatItsFramesAre:
    def test_the_picker_emits_a_concrete_stream_type(self) -> None:
        """Both tuples, because one unstated is enough to switch the check off.

        `ArraySpec.admits` is false only where the two sides are provably
        disjoint, so a wildcard on either axis admits everything: an `emits` with
        an empty `dtypes` would pass against every `accepts` on the shelf, and
        `dag.py`'s edge check would be retired for every graph holding a picker.
        The second assertion is that claim made positive — a downstream this
        tool genuinely cannot feed is refused, which is only possible because
        both tuples are stated.
        """
        discover()
        emits = PickParams.spec().emits
        assert isinstance(emits, ArraySpec)

        assert emits.dtypes, "an unstated dtype admits every input on the shelf"
        assert emits.channels, "an unstated channel layout admits every input on the shelf"
        assert not ArraySpec(dtypes=("float32",)).admits(emits)
        assert not ArraySpec(channels=(ChannelSpec.RGB,)).admits(emits)
