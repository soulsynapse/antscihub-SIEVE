"""Secret: what a pipeline value is and how it lowers to a graph.

Chunk 6. A pipeline is a source name and an ordered list of (tool, params)
steps — a value, not a graph. Lowering it walks the steps through each
tool's ``lower`` (chunk 5) to produce the ``Node`` the executor evaluates.
Nothing outside this module may depend on the JSON shape (field names) —
only on ``to_json`` / ``from_json`` round-tripping and on ``lower``
producing the same graph a hand-built one would. Where a pipeline *lives* —
a name resolving to a file on disk — is ``store.py``'s secret, not this
module's; this file never touches a path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from proto_sieve.src.sieve.kernel import Node, Source
from proto_sieve.src.sieve.tools.crop import Crop, CropParams

# Every tool this spike knows how to lower, by the name a step file uses.
_TOOLS: dict[str, tuple[type, type]] = {
    "crop": (Crop, CropParams),
}


@dataclass(frozen=True)
class Step:
    tool: str
    params: dict[str, Any]


@dataclass(frozen=True)
class Pipeline:
    source: str
    steps: tuple[Step, ...]


def to_json(pipeline: Pipeline) -> str:
    payload = {
        "source": pipeline.source,
        "steps": [{"tool": s.tool, "params": s.params} for s in pipeline.steps],
    }
    return json.dumps(payload, sort_keys=True)


def from_json(blob: str) -> Pipeline:
    data = json.loads(blob)
    steps = tuple(Step(tool=s["tool"], params=s["params"]) for s in data["steps"])
    return Pipeline(source=data["source"], steps=steps)


def tool_for(name: str) -> tuple[type, type]:
    """The (Tool, params) pair a step file's tool name resolves to."""
    return _TOOLS[name]


def lower(pipeline: Pipeline) -> Node:
    """A pipeline value to the graph a hand-built one would produce."""
    node = Node(Source(pipeline.source))
    for step in pipeline.steps:
        tool_cls, params_cls = _TOOLS[step.tool]
        params = params_cls(**step.params)
        node = tool_cls().lower(params, node)
    return node
