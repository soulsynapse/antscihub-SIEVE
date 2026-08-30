"""The chain as a document: what nodes exist, and what feeds what.

Structure only. Whether a binding is *legal* — that the producer offers a
product of the kind the consumer wants, in a form it can be served — needs
the producer open, so it lives in `bind.py` where the real outputs are. What
is checkable with nothing open is checked here: that ids are unique, that a
step is fed exactly once, and that nothing feeds itself around a loop.

**A node id is not a tool name.** Two crops of one step are two nodes of one
tool, and both offer `"flow"` (`nodes.Produced` is tool-local by design), so
the id is what a binding names and what a key is filed under. It survives the
tool being renamed and it is what a persistent form would carry, which is why
it is a field rather than an index into a list.

**The head is a requirement, not a recording.** A source node names the tool
that will open something, never what it opens: a pipeline is not a property
of a recording, and an address written in here is the one fact that would
stop the same chain being applied to the next forty files.
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.contract import Tool


@dataclass(frozen=True)
class Node:
    """One tool placed in the chain, under an id the chain owns."""

    id: str
    tool: Tool

    @property
    def kind(self) -> str:
        return self.tool.kind


@dataclass(frozen=True)
class Binding:
    """One node's product, feeding one node's want."""

    producer: str   #: node id of whatever answers
    product: str    #: which of that node's products
    consumer: str   #: node id of the step being fed


@dataclass(frozen=True)
class Chain:
    """The nodes and the bindings between them."""

    nodes: tuple[Node, ...]
    bindings: tuple[Binding, ...] = ()

    def __post_init__(self) -> None:
        ids = [node.id for node in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{sorted(ids)} names one node twice")
        known = set(ids)
        for binding in self.bindings:
            for end in (binding.producer, binding.consumer):
                if end not in known:
                    raise ValueError(f"{binding} names {end!r}, which is not a node")
            if binding.producer == binding.consumer:
                raise ValueError(f"{binding.consumer!r} feeds itself")
        for node in self.nodes:
            feeding = [b for b in self.bindings if b.consumer == node.id]
            if node.kind == "source" and feeding:
                raise ValueError(f"{node.id!r} is a source and takes no input")
            if node.kind == "step" and len(feeding) != 1:
                # One want, for now. A step taking two inputs is a change to
                # the contract's consumer side, and this becomes a count.
                raise ValueError(
                    f"{node.id!r} is fed {len(feeding)} times; a step wants one")
        self._ordered()

    def node(self, id: str) -> Node:
        for node in self.nodes:
            if node.id == id:
                return node
        raise KeyError(id)

    def feeding(self, consumer: str) -> Binding | None:
        """The binding that answers *consumer*'s want, or None for a head."""
        for binding in self.bindings:
            if binding.consumer == consumer:
                return binding
        return None

    def order(self) -> tuple[Node, ...]:
        """Every node, producers before whatever they feed."""
        return self._ordered()

    def _ordered(self) -> tuple[Node, ...]:
        """Topological, and the cycle check: a loop never drains."""
        placed: list[Node] = []
        seen: set[str] = set()
        left = list(self.nodes)
        while left:
            ready = [node for node in left
                     if (feeding := self.feeding(node.id)) is None
                     or feeding.producer in seen]
            if not ready:
                raise ValueError(
                    f"{sorted(node.id for node in left)} feed each other in a loop")
            for node in ready:
                placed.append(node)
                seen.add(node.id)
                left.remove(node)
        return tuple(placed)

    def key(self, id: str) -> str:
        """The durable spelling of *id*'s output, upstream folded in front.

        ADR-0010's fold — name, version and the params the answer depends on —
        with the producer's key ahead of it, because the same step over
        different upstream work is different work. That prefix is why a fifth
        crop re-runs one branch and reuses four, and it is the one part of a
        key no tool can spell for itself.
        """
        node = self.node(id)
        params = getattr(node.tool.role, "params", None)
        stem = f"{node.tool.name}@{node.tool.version}"
        if params:
            bits = ",".join(f"{name}={params[name]}" for name in sorted(params))
            stem = f"{stem}({bits})"
        feeding = self.feeding(id)
        if feeding is None:
            return stem
        return f"{self.key(feeding.producer)}>{feeding.product}>{stem}"
