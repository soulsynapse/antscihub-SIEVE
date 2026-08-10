"""A checkpoint on disk stands back in the graph as the node that wrote it.

Three claims, and none of them is about numpy. The first is the crop half's
sentence for the other artifact: a file where a node stood serves the graph
below it identically, through the ordinary source-root machinery, with no front
end learning that artifacts exist. The second is the fact minting that root
would otherwise have hardwired a gap into — a `.npy` has to say which product of
its node it holds, or a reader cannot check it against the claim it was made for
and two products of one node overwrite each other. The third is where the halves
part: a written crop is read through `decode/` and folds the string its footage
folds, and a checkpoint is not, so its root is keyed off the written file
(`adr/a-root-keys-by-its-reader.md`).

Driven through `sieve run` for `test_checkpoints.py`'s reason: what would
plausibly break lives between the document and the loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import yaml
from numpy.typing import NDArray
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, SourceSpan
from sieve.core.tool_base import SOLE_PORT
from sieve.decode.reader import VideoReader
from sieve.pipeline.cache_key import node_key, picked_key, source_identity, source_key
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan, validated_params
from sieve.pipeline.resolve_source import anchored, picked_identities, source_files
from sieve.storage.checkpoint_writer import BASELINE_DIR, MANIFEST_NAME, checkpoints_dir
from sieve.tools import discover
from tests.projects import footage_of, project_over

runner = CliRunner()

PROJECT_NAME = "arena.sieve.yaml"
CUT = "cut"
DOWN = "down"
AGAIN = "again"
READ = "read"
SIG = "sig"
SPAN = SourceSpan(start=10, end=16)

#: `downsample`'s one emission, which names the file the writer produces. Spelt
#: here rather than read off the spec: a name derived the way the writer derives
#: it would pass for a writer that had stopped naming the product at all.
DOWN_PRODUCT = "downsampled"

#: What a checkpoint is taken of: a crop, then a reduction worth not repeating.
WRITING = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
    ),
    edges=(Edge(upstream=CUT, downstream=DOWN),),
)

#: The same graph with one more step, which is the run the read-back has to
#: reproduce: everything below the checkpointed node, computed the long way.
COMPUTING = Pipeline(
    nodes=(
        *WRITING.nodes,
        Node(node_id=AGAIN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
    ),
    edges=(*WRITING.edges, Edge(upstream=DOWN, downstream=AGAIN)),
)


def _project(
    video: Path,
    directory: Path,
    *,
    pipeline: Pipeline,
    checkpoints: tuple[str, ...] = (),
) -> Path:
    """Write the project into `directory` and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    project = project_over(video, directory, pipeline).model_copy(
        update={"checkpoints": checkpoints}
    )
    path = directory / PROJECT_NAME
    Project.model_validate(project).save(path)
    return path


def _run(project_path: Path) -> str:
    result = runner.invoke(app, ["run", str(project_path), "--frames", f"{SPAN.start}:{SPAN.end}"])
    assert result.exit_code == 0, result.output
    return result.output


def _computed(project_path: Path, node_id: str) -> list[NDArray[Any]]:
    """What a run of this document produces in memory, frame by frame."""
    discover()
    project = Project.load(project_path)
    video = footage_of(project, project_path)
    # Anchored and picked: the footage is a source root now
    # (`adr/a-document-names-footage-only-through-a-tool.md`), so the graph has
    # to be resolved against the project's own directory and its file's identity
    # has to reach the keys, exactly as `sieve run` does both.
    dag = Dag.build(anchored(project.pipeline, project_path.parent))
    plan = ExecutionPlan.build(
        dag,
        source=source_identity(video),
        span=SPAN,
        picked=picked_identities(source_files(dag, validated_params(dag, None))),
    )
    with VideoReader(video, luma=plan.luma) as reader:
        return [np.array(result[node_id].data) for result in execute(plan, reader)]


def _written(video: Path, directory: Path, node_id: str, product: str) -> Path:
    """The file a baseline run of `directory`'s project wrote for `node_id`."""
    return checkpoints_dir(video, directory) / BASELINE_DIR / f"{node_id}.{product}.npy"


def _reading(stack: Path, downstream: bool) -> Pipeline:
    """A pipeline rooted on `stack`, standing where `DOWN` stood.

    The node keeps the id nothing else in the graph needs to know changed, which
    is the substitution's whole shape: a consumer of the checkpointed node is a
    consumer of the file that holds its output.
    """
    root = Node(
        node_id=READ,
        tool_id="checkpoint",
        version="1.0.0",
        params={"path": str(stack), "first_index": SPAN.start},
    )
    if not downstream:
        return Pipeline(nodes=(root,))
    return Pipeline(
        nodes=(
            root,
            Node(node_id=AGAIN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
        ),
        edges=(Edge(upstream=READ, downstream=AGAIN),),
    )


class TestAStretchComesBackAsANode:
    def test_a_checkpointed_stretch_is_read_back_as_a_source_tool(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The graph below the file computes exactly what it computed before.

        Compared against the run that computes the whole chain, so the assertion
        cannot be satisfied by both sides sharing a mistake the read-back
        introduced. Fails for a tool that hands rows back under its file's own
        numbering rather than the source's — the fixture's per-frame ramp turns
        an off-by-one into a mismatch — and for one that never reached the graph
        at all, since `AGAIN` is a real node fed by the root.
        """
        expected = _computed(
            _project(synthetic_video, tmp_path / "long", pipeline=COMPUTING), AGAIN
        )
        writing = tmp_path / "writing"
        _run(_project(synthetic_video, writing, pipeline=WRITING, checkpoints=(DOWN,)))
        stack = _written(synthetic_video, writing, DOWN, DOWN_PRODUCT)

        reading = tmp_path / "reading"
        _run(
            _project(
                synthetic_video,
                reading,
                pipeline=_reading(stack, downstream=True),
                checkpoints=(AGAIN,),
            )
        )

        served = np.load(_written(synthetic_video, reading, AGAIN, DOWN_PRODUCT))
        assert served.shape == (SPAN.frame_count, *expected[0].shape)
        for row, frame in enumerate(expected):
            assert np.array_equal(served[row], frame), f"frame {SPAN.start + row}"

    def test_the_read_back_graph_opens_no_container_and_holds_no_computing_node(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """What makes it the source-tool mechanism rather than a second path.

        The root is a root by declaration — nothing feeds it, and `Dag` counts
        it among the roots that open their own file — so `sieve run` opens the
        parent for nothing and no front end has a route to learn.
        """
        writing = tmp_path / "writing"
        _run(_project(synthetic_video, writing, pipeline=WRITING, checkpoints=(DOWN,)))
        stack = _written(synthetic_video, writing, DOWN, DOWN_PRODUCT)

        discover()
        dag = Dag.build(_reading(stack, downstream=True))

        assert [node.node_id for node in dag.source_roots] == [READ]
        assert dag.source_roots == dag.roots
        assert dag.elements[READ] is None, "a .npy does not record what one value is a value of"


class TestTheFileSaysWhatItIs:
    def test_a_checkpoints_identity_names_the_product_it_holds(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Two products of one node are two files, and the manifest says which.

        `block_signal` is the tool the gap was measured on: one node, four
        measurements, and a `.npy` of float32 that could be any of them. The two
        runs differ in the selecting parameter and in nothing else, so a writer
        naming files by node alone would have the second silently replace the
        first — and `cache_key.source_identity`, which is a path and two stats,
        could not tell the two apart afterwards.
        """
        directory = tmp_path / "signals"
        for signal in ("change_energy", "coherence"):
            _project(
                synthetic_video,
                directory,
                pipeline=Pipeline(
                    nodes=(
                        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
                        Node(
                            node_id=SIG,
                            tool_id="block_signal",
                            version="1.0.0",
                            params={"signal": signal, "block": 8},
                        ),
                    ),
                    edges=(Edge(upstream=CUT, downstream=SIG),),
                ),
                checkpoints=(SIG,),
            )
            _run(directory / PROJECT_NAME)

        energy = _written(synthetic_video, directory, SIG, "change_energy")
        coherence = _written(synthetic_video, directory, SIG, "coherence")
        assert energy.exists() and coherence.exists()
        assert source_identity(energy) != source_identity(coherence)

        folder = checkpoints_dir(synthetic_video, directory) / BASELINE_DIR
        manifest = yaml.safe_load((folder / MANIFEST_NAME).read_text(encoding="utf-8"))
        (entry,) = manifest["entries"]
        assert entry["emission"] == "coherence"
        assert entry["file"] == coherence.name


class TestTheRootIsKeyedOffTheFile:
    def test_a_read_back_root_is_keyed_off_the_written_file(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """`picked_key`, not `source_key`, and not the key the node was written under.

        The half of `adr/a-root-keys-by-its-reader.md` the crop half could not
        show: `footage` reads through `decode/` and folds the string its file
        would fold as footage, and this tool does not, so the flavour differs for
        two source roots over two artifacts. Fails for a `checkpoint` tool that
        declared `decoded = True` — which would key a `.npy` against a video
        decoder that never opened it — and for any wiring that carried the
        checkpointed node's own key across as the root's ancestor.
        """
        writing = tmp_path / "writing"
        written_path = _project(synthetic_video, writing, pipeline=WRITING, checkpoints=(DOWN,))
        _run(written_path)
        stack = _written(synthetic_video, writing, DOWN, DOWN_PRODUCT)

        discover()
        dag = Dag.build(_reading(stack, downstream=False))
        identity = source_identity(stack)
        keys = dag.node_keys(source=source_identity(synthetic_video), picked={READ: identity})

        node = dag.order[0]
        spec = dag.specs[READ]
        assert keys[READ] == node_key(
            node, spec=spec, upstream=((SOLE_PORT, picked_key(identity)),)
        )
        assert keys[READ] != node_key(
            node,
            spec=spec,
            upstream=((SOLE_PORT, source_key(identity, decode_format="luma")),),
        )

        written = Project.load(written_path)
        writer_plan = ExecutionPlan.build(
            Dag.build(written.pipeline),
            source=source_identity(synthetic_video),
            span=SPAN,
        )
        assert keys[READ] != writer_plan.key(DOWN), "the file is the ancestry, not the graph"

    def test_replacing_the_file_moves_the_key(self, synthetic_video: Path, tmp_path: Path) -> None:
        """The failure `picked_key` exists to close, on this tool's file.

        A stack swapped for another under one path has to be a different
        computation, or the store serves the first result under the second's
        name — well-formed key, plausible frame, no symptom.
        """
        writing = tmp_path / "writing"
        _run(_project(synthetic_video, writing, pipeline=WRITING, checkpoints=(DOWN,)))
        stack = _written(synthetic_video, writing, DOWN, DOWN_PRODUCT)

        discover()
        dag = Dag.build(_reading(stack, downstream=False))
        source = source_identity(synthetic_video)
        before = dag.node_keys(source=source, picked={READ: source_identity(stack)})

        np.save(stack, np.zeros((SPAN.frame_count, 4, 4), dtype="uint8"))
        after = dag.node_keys(source=source, picked={READ: source_identity(stack)})

        assert before[READ] != after[READ]
