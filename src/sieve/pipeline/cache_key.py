"""What makes two computations the same computation.

A cache key answers one question: has this exact result been produced before?
Everything that could change the bytes has to be in it, and nothing that cannot
may be, because the two failure modes are not symmetric. An input left out is a
wrong answer served from cache and never noticed — the run completes, the
numbers are plausible, and the only evidence is that a re-run on a cleared cache
disagrees. An input wrongly included is a cache miss: slower, correct, obvious.
So where a judgement call exists below it goes the second way.

**The key is per node, not per graph.** `node_key` takes the keys of the nodes
feeding it and folds them in, so a key transitively covers the whole ancestry —
which is what makes guardrail §5 fall out rather than be enforced. Two sibling
branches share their ancestors' keys and nothing else, so editing a parameter on
one changes that branch and everything below it, and cannot reach the other. The
*walk* — which nodes, in what order — is not here: it needs a topological sort,
that is `dag.py`'s, and a second traversal written against a graph it did not
validate is a second answer to the question of what the graph is.

**Decoder identity enters once, at the root.** It is folded into `source_key`,
which every root node names as its upstream, so it reaches every downstream key
through the ancestry rather than by being re-hashed at each node. Backend
identity is the opposite: it enters at *every* node, because two nodes in one
graph can run on different backends, and it drops out only where the filter has
claimed `backend_agnostic`.

**What is deliberately absent.** The requested clip range, checkpoints, sink
paths, and the replicate's display name. A clip changes which frames are
computed, never what a frame is — so `ExecutionPlan.span` reaches nothing here,
and a caller narrowing what it asks for keeps every entry it had.

That is a statement about the *request*, and `filters/span.py` is deliberately
not an exception to it. A span node is a node: its parameters are hashed like any
other filter's, because a graph that selects is a different graph and the
alternative — a field the fold skips — is an input left out, which is this
module's first paragraph. The price is real and is charged where it can be
avoided: those parameters land in the key of everything *downstream* of the node,
so a span at a root re-derives the whole chain when its bounds move, for frames
whose pixels did not. `span.md` says to put it at a leaf, and that is what the
advice is made of.

A checkpoint changes where a result lives, never what it is —
`Project` keeps both off `Node` for this reason, and hashing them here would
undo that: an HPC handoff empties `checkpoints` (VISION step 6) and must not
invalidate a single entry. A sink path is where output is written, and two
projects writing the same computation to different folders share entries. A
replicate is identified by `replicate_id` precisely so renaming one costs
nothing, and even `replicate_id` is absent — what separates two replicates is
their ROI, which is in the key, and two arenas that genuinely cropped the same
pixels and ran the same parameters *are* the same computation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path, PurePosixPath

from sieve.backend.dispatch import Backend
from sieve.backend.identity import backend_identity
from sieve.core.filter_base import FilterSpec, Mode
from sieve.core.pipeline_model import Node, resolved_params
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.decode.identity import decoder_identity
from sieve.decode.lowered import LoweredPrefix

#: Seeds every key. Bumping it invalidates the whole cache in one edit, which is
#: the remedy when a *derivation* changes — a field added to a key, a canonical
#: form that stops being canonical — as opposed to when an input changes. Without
#: it the only way to correct a key that was missing an input would be to touch
#: every input by hand.
#:
#: 2: the upstream fold gained port names (2026-07-26, multi-upstream kernels).
#: A sorted list of upstream keys could not tell `a - b` from `b - a`; the fold
#: is now `[port, key]` pairs, which changes every node key's derivation.
#: 3: `source_key` gained the decode format (2026-07-27, the luma path). This is
#: the case the paragraph above names — a field added to a key — and the bump is
#: belt and braces: appending the field already changes every root digest, and
#: `DECODE_POLICY_VERSION` moved in the same commit for a different reason. All
#: three invalidate the same entries once, and each records a distinct fact.
HASH_VERSION = 3

#: 32 bytes of BLAKE2b. Not a security boundary — nothing here defends against a
#: crafted collision — so the size is chosen against accidental collision, where
#: 256 bits is far past the point of ever being the reason a run is wrong.
DIGEST_BYTES = 32


class NotCacheableError(ValueError):
    """A key was requested for a filter whose output cannot be safely keyed.

    Raising rather than returning a key is what makes non-cacheability
    propagate. A node with no key gives its downstream no upstream hash to
    fold in, so the whole subtree below a non-cacheable filter is uncacheable
    without anything having to compute that fact — which is correct, because a
    downstream result is only reusable if what it was computed from was.

    Callers that can proceed either way check `is_cacheable` first.
    """


class CachePolicy(StrEnum):
    """The cache-key layer's decision from spec facts and the cache contract."""

    KEYED = "keyed"
    NOT_DETERMINISTIC = "not_deterministic"
    STATEFUL_ORIGIN = "stateful_origin"
    WINDOWED_FRONTIER = "windowed_frontier"


def cache_policy(spec: FilterSpec) -> CachePolicy:
    """Whether this spec may have a node key under the current cache contract.

    This is policy, not a `FilterSpec` fact. The spec declares whether a filter
    is deterministic, stateful, and windowed; this layer decides whether the
    current `(node key, source index)` store can stand behind a hit for that
    combination.
    """
    if not spec.deterministic:
        return CachePolicy.NOT_DETERMINISTIC
    if spec.stateful:
        return CachePolicy.STATEFUL_ORIGIN
    if spec.mode is not Mode.STREAMING:
        return CachePolicy.WINDOWED_FRONTIER
    return CachePolicy.KEYED


def is_cacheable(spec: FilterSpec) -> bool:
    """Whether `node_key` will derive a key for `spec`."""
    return cache_policy(spec) is CachePolicy.KEYED


def _uncacheable_clause(spec: FilterSpec) -> str:
    """Why the refusal happened, said off `cache_policy` and not off the spec.

    Reading the spec a second time here is how the message and the decision
    drift apart: the three disqualifications are ordered, so a spec that is
    both stateful and windowed is refused for one reason and could be
    explained by another. One derivation, consulted twice.
    """
    match cache_policy(spec):
        case CachePolicy.NOT_DETERMINISTIC:
            return "is not deterministic, so its output cannot be keyed"
        case CachePolicy.STATEFUL_ORIGIN:
            return "is stateful, so its output cannot be keyed"
        case CachePolicy.WINDOWED_FRONTIER:
            return f"declares mode={spec.mode}, so its provisional windowed output cannot be keyed"
        case CachePolicy.KEYED:
            raise AssertionError(f"{spec.filter_id} is cacheable; there is no refusal to explain")


def _digest(*parts: object) -> str:
    """Hash a fixed-arity list of JSON-representable parts.

    A JSON array rather than a delimiter join, so that no part can impersonate a
    boundary: a filter id containing whatever character was chosen as a
    separator would otherwise let two different inputs produce one string. The
    arity is fixed per key flavour and the positions are meaningful, so an
    absent input is `None` in place rather than a shorter list.
    """
    payload = json.dumps([HASH_VERSION, *parts], separators=(",", ":"))
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=DIGEST_BYTES).hexdigest()


def source_identity(video: Path) -> str:
    """A string that changes when the footage at `video` changes.

    Path, size, and modification time — *not* a content hash. Hashing the file
    is the honest answer and it costs a full read of a multi-gigabyte video
    every time a project opens, which is in the budget for nothing. The three
    cheap facts fail in one direction each, and both failures were weighed:

    - A file edited in place preserving both size and mtime hashes alike and
      would be served stale. This requires deliberate effort to produce.
    - Footage copied to another machine, or restored from a backup, gets a new
      identity and recomputes. Wasteful, correct, and the common case.

    The path is included because size and mtime alone are not distinctive
    enough: copying a directory with `cp -p` gives every file in it the same
    mtime, and two takes from one camera can be byte-identical in length.

    Raises:
        OSError: if `video` does not exist — a key over absent footage would be
            a key for a run that cannot happen.
    """
    stat = video.stat()
    return f"{PurePosixPath(video.resolve()).as_posix()}|{stat.st_size}|{stat.st_mtime_ns}"


def source_key(
    source: str,
    roi: ROI | None = None,
    *,
    luma: bool = False,
    lowered_prefix: LoweredPrefix | None = None,
) -> str:
    """The key for frames as one replicate sees them: the ancestor of every root.

    `roi` is the replicate's crop, and it is here rather than on the first node
    because the graph never observes an uncropped frame — the fan-out has
    already happened by the time a root runs, so the crop is a property of the
    source this replicate was handed. `None` is a project with no replicates,
    which is the whole frame and a different key from any crop of it.

    `luma` is the decode format, and it belongs here for the same reason
    `decoder_identity()` does: it changes the pixel values every root is handed.
    A graph that reads no chroma is decoded from the luma plane rather than from
    a BGR conversion of it (`decode/reader.py`), and the two are not the same
    array — so a colour graph and a luma graph over one file must not collide.
    `Dag.needs_chroma` derives it; nothing chooses it by hand, which is what
    stops the key and the reader disagreeing.

    Note what this is *not*: it is not the fact that this package's decode policy
    changed when the luma path landed. That is every entry ever computed, it is
    not per-run, and it is `DECODE_POLICY_VERSION` inside `decoder_identity()`.
    This field distinguishes two runs on one build; that constant distinguishes
    two builds.

    **Whether a materialized crop exists does not appear here, and must not.**
    Not because it cannot change a key — under the child-source model settled
    2026-07-28 it does, and knowingly — but because the way it does is by being
    passed a *different `source`*, computed from the artifact file itself
    (`pipeline/resolve_source.py`). This function is never asked "is there a
    crop"; it is handed footage and a region, and an artifact is footage. A
    presence test in here would be the storage-decision-as-semantic-decision the
    earlier byte-parity model was written to avoid, and it would additionally
    be a second answer to a question `resolve_source` already owns.

    The `roi` argument is where that lands: a run over the parent names the
    replicate's region, a run over that replicate's artifact names none, because
    the region was cut before the file existed. `ExecutionPlan.roi` is the one
    place those two are told apart. See
    `docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md` for why the crop
    is in the graph at all, and `CropArtifact` for what re-keying onto a child
    source buys and costs.

    Args:
        source: What identifies the footage — `source_identity` builds one.
        roi: The replicate's region, in source pixels.
        luma: Whether the source is decoded as single-channel luma. Defaults to
            colour, so a caller that has not thought about it gets the format
            that has always been the default rather than a silently cheaper one.
    """
    region = None if roi is None else [roi.x, roi.y, roi.width, roi.height]
    if lowered_prefix is None:
        return _digest("source", source, decoder_identity(), region, "luma" if luma else "bgr")
    if roi is not None:
        raise ValueError("a lowered source carries its crop in the lowered prefix")
    if not luma:
        raise ValueError("a lowered source emits gray frames and must be keyed as luma")
    return _digest(
        "source",
        source,
        lowered_prefix.decoder_identity,
        None,
        "luma",
        lowered_prefix.cache_parts(),
    )


def node_key(
    node: Node,
    *,
    spec: FilterSpec,
    upstream: Mapping[str, str],
    backend: Backend,
    replicate: Replicate | None = None,
) -> str:
    """The key for `node`'s output, for one replicate, on one backend.

    Takes the `Node` and the `Replicate` rather than a parameter dict, and that
    is the point of the signature: `resolved_params` is applied here, so there
    is no argument position into which `Node.params` could be passed by mistake.
    Hashing the node's own dict would be wrong in both directions — it moves on
    every edit anywhere in the fan-out, so it invalidates twelve entries for a
    change one replicate saw, and it is not what a replicate carrying an
    override actually runs with.

    The resolved dict is validated against `spec.params_model` before it is
    hashed, which is what makes the key canonical rather than merely
    deterministic: defaults are filled in, so a document that omits `factor` and
    one that spells out `factor: 2` are one computation and not two, and enums
    and paths reach the digest as the strings they became in the artifact.

    Args:
        node: The graph node. Its `filter_id` and `version` must match `spec`.
        spec: The registered filter, resolved by the caller — `dag.py` does this
            against a `FilterRegistry` and the executor carries the result.
        upstream: Port name to the key of the node feeding it — the
            `source_key` under the root's one declared port for a root. The
            port names are *in* the digest, bound to their keys, because which
            port a stream arrives on is part of what a merging node computes:
            `a - b` and `b - a` are fed by the same two keys and are not the
            same computation. Hashed as sorted pairs, so edge declaration
            order still cannot move a key.
        backend: Where this node runs. Absent from the key exactly when the
            filter has claimed its kernels agree bit for bit.
        replicate: The replicate being processed; `None` for the node's
            baseline, which is what a project with no fan-out runs.

    Raises:
        NotCacheableError: if `spec` has not claimed `deterministic`.
        ValueError: if `spec` describes a different filter than `node` names.
        ValidationError: if the resolved parameters are not valid for
            `spec.params_model` — a misspelled key, or a value out of range.
    """
    if spec.key != (node.filter_id, node.version):
        raise ValueError(
            f"spec is {spec.filter_id} {spec.version} but node names "
            f"{node.filter_id} {node.version}"
        )
    if not is_cacheable(spec):
        raise NotCacheableError(
            f"{spec.filter_id} {spec.version} {_uncacheable_clause(spec)} — nothing that reads "
            "such an entry can know it matches what would be recomputed"
        )
    params = spec.params_model.model_validate(resolved_params(node, replicate))
    return _digest(
        "node",
        sorted([port, key] for port, key in upstream.items()),
        node.filter_id,
        node.version,
        params.canonical_json(),
        None if spec.backend_agnostic else backend_identity(backend),
    )
