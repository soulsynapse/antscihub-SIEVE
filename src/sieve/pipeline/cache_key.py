"""What makes two computations the same computation.

A cache key answers one question: has this exact result been produced before?
Everything that could change the bytes has to be in it, and nothing that cannot
may be, because the two failure modes are not symmetric. An input left out is a
wrong answer served from cache and never noticed — the run completes, the
numbers are plausible, and the only evidence is that a re-run on a cleared cache
disagrees. An input wrongly included is a cache miss: slower, correct, obvious.
So where a judgement call exists below it goes the second way.

**The key is per node, not per graph.** `node_key` takes the key of the node
feeding it and folds it in, so a key transitively covers the whole ancestry.
Two sibling branches share their ancestors' keys and nothing else, so editing a
parameter on one changes that branch and everything below it, and cannot reach
the other. The *walk* — which nodes, in what order — is not here: it needs a
topological sort, that is `dag.py`'s, and a second traversal written against a
graph it did not validate is a second answer to the question of what the graph
is.

**Decoder identity enters once, at the root.** It is folded into `source_key`,
which a root the footage feeds names as its upstream, so it reaches every
downstream key through the ancestry rather than by being re-hashed at each node.
Which of the two flavours a root that opens its own file names follows the
*reader* and nothing else (`adr/a-root-keys-by-its-reader.md`): a file read
through `decode/` folds `source_key` like any footage, and only a tool reading
with its own code folds `picked_key`. The two are what keeps one graph's two
roots from folding one identity.

**What is deliberately absent.** Checkpoints, sink paths, the frames a run asks
for, the replicate's display name, and a source tool's path parameter — the last
being the one absence that is a parameter, argued at `node_key`. Narrowing a request changes which frames
are computed, never what a frame is, and `tools/span.py` is deliberately not an
exception to that: a span node is a node, its parameters are hashed like any
other tool's, because a graph that selects is a different graph and the
alternative — a field the fold skips — is an input left out, which is this
module's first paragraph. The price is real and is charged where it can be
avoided: those parameters land in the key of everything *downstream* of the
node, so a span at a root re-derives the whole chain when its bounds move, for
frames whose pixels did not.

A checkpoint changes where a result lives, never what it is — `Project` keeps
`checkpoints`, `outputs` and `crops` off `Node` for this reason, and hashing
them here would undo that: an HPC handoff empties `checkpoints` (VISION step 6)
and must not invalidate a single entry. A sink path is where output is written,
and two projects writing the same computation to different folders share
entries. A replicate is identified by `replicate_id` precisely so renaming one
costs nothing, and even `replicate_id` is absent — what separates two replicates
is what they resolve their parameters to, which is in the key, and two arenas
that genuinely ran the same settings over the same pixels *are* the same
computation.

**Where v2's geometry went.** A replicate's box was a field on the replicate and
was folded into the source key; in schema v1 it is the crop node's `region`
parameter, deviated per replicate (`adr/detector-is-a-node.md`). So it enters
through `resolved_params` like any other parameter, and this module needs no
notion of a region at all — which also means the separation is per *node*, at
the node that does the cutting, rather than applied to a whole graph's ancestry.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path, PurePosixPath

from sieve.core.pipeline_model import CropFormat, Node, Replicate, resolved_params
from sieve.core.tool_base import Mode, ToolSpec, WarmupKind
from sieve.decode.identity import decoder_identity

#: Seeds every key. Bumping it invalidates the whole cache in one edit, which is
#: the remedy when a *derivation* changes — a position added to a key, a
#: canonical form that stops being canonical — as opposed to when an input
#: changes. Without it the only way to correct a key that was missing an input
#: would be to touch every input by hand.
#:
#: Moved to 2 when `upstream` below became port-bound pairs. Every node with an
#: ancestor keys differently under the new layout, so the whole store turns over
#: once — which is what this constant is for, and is cheaper than the alternative
#: of a layout that could be read two ways.
HASH_VERSION = 2

#: 32 bytes of BLAKE2b. Not a security boundary — nothing here defends against a
#: crafted collision — so the size is chosen against accidental collision, where
#: 256 bits is far past the point of ever being the reason a run is wrong.
DIGEST_BYTES = 32

#: The ordered positions of a node digest, and the pin `test_cache_key.py`
#: asserts character-exact. `_digest` refuses a part list of a different length,
#: so this is what a position has to be added to before it can be hashed —
#: which is the difference between a layout change that shows up in a diff and
#: one that shows up as a cache that silently stops hitting.
#:
#: `flavour` is the literal tag that keeps the two key kinds from colliding.
#: `upstream` is v2's port-to-key mapping, back with the merging protocol: an
#: ordered list of `(port, key)` pairs, one per input, `port` being `SOLE_PORT`
#: on the single-input nodes that are most of every graph. It is the wiring the
#: digest has to distinguish — the same two upstreams crossed over feed the same
#: two keys and are not the same computation.
NODE_KEY_POSITIONS: tuple[str, ...] = ("flavour", "upstream", "tool_id", "version", "params")

#: `NODE_KEY_POSITIONS` for the ancestor of every root the footage feeds.
SOURCE_KEY_POSITIONS: tuple[str, ...] = ("flavour", "source", "decoder", "format")

#: `NODE_KEY_POSITIONS` for the ancestor of a root that reads its own file.
#: Neither of `source_key`'s last two positions appears, and their absence is
#: the difference between the two flavours rather than an omission — see
#: `picked_key`.
PICKED_KEY_POSITIONS: tuple[str, ...] = ("flavour", "file")


class NotCacheableError(ValueError):
    """A key was requested for a tool whose output cannot be safely keyed.

    Raising rather than returning a key is what makes non-cacheability
    propagate. A node with no key gives its downstream no upstream hash to fold
    in, so the whole subtree below a non-cacheable tool is uncacheable without
    anything having to compute that fact — which is correct, because a
    downstream result is only reusable if what it was computed from was.

    Callers that can proceed either way check `is_cacheable` first.
    """


class CachePolicy(StrEnum):
    """The cache-key layer's decision from spec facts and the cache contract."""

    KEYED = "keyed"
    NOT_DETERMINISTIC = "not_deterministic"
    EPSILON_WARMUP = "epsilon_warmup"
    STATEFUL_WINDOW = "stateful_window"


def cache_policy(spec: ToolSpec) -> CachePolicy:
    """Whether this spec may have a node key under the current cache contract.

    This is policy, not a `ToolSpec` fact. The spec declares what determines its
    output; this layer decides whether the current `(node key, source index)`
    store and the executor behind it can stand behind a hit for that
    combination.

    **The question is how far back the output depends, not whether state was
    kept** (`adr/cache-admission-is-bounded-warmup.md`). A bounded warmup means
    the last `W + 1` frames decide the answer, so a run that re-settles over `W`
    computes what the entry holds; an epsilon warmup means the run's origin
    never quite leaves the answer, and no key carries an origin. Until 06.5 this
    read `stateful`, which refused `block_signal` (one frame of state, exact)
    and `background_ema` (the same declaration, unbounded) for one reason that
    was only true of the second.

    A window is bounded on both sides by construction, so `Mode` no longer
    decides anything here on its own. It reappears in one place: the executor
    re-settles a state by replaying single frames, which a *windowed* state
    would need its windows replayed for, and no tool declares both — so the
    combination is refused rather than served by a loop that cannot honour it.
    """
    if not spec.deterministic:
        return CachePolicy.NOT_DETERMINISTIC
    if spec.warmup_kind is WarmupKind.EPSILON:
        return CachePolicy.EPSILON_WARMUP
    if spec.stateful and spec.mode is not Mode.STREAMING:
        return CachePolicy.STATEFUL_WINDOW
    return CachePolicy.KEYED


def is_cacheable(spec: ToolSpec) -> bool:
    """Whether `node_key` will derive a key for `spec`."""
    return cache_policy(spec) is CachePolicy.KEYED


def _uncacheable_clause(spec: ToolSpec) -> str:
    """Why the refusal happened, said off `cache_policy` and not off the spec.

    Reading the spec a second time here is how the message and the decision
    drift apart: the three disqualifications are ordered, so a spec that is both
    stateful and windowed is refused for one reason and could be explained by
    another. One derivation, consulted twice.
    """
    match cache_policy(spec):
        case CachePolicy.NOT_DETERMINISTIC:
            return "is not deterministic, so its output cannot be keyed"
        case CachePolicy.EPSILON_WARMUP:
            return (
                f"declares an epsilon warmup, so its output at a frame still carries where the "
                f"run began — to within {spec.settling_epsilon}, which is not to within nothing"
            )
        case CachePolicy.STATEFUL_WINDOW:
            return (
                f"is stateful and declares mode={spec.mode}, and the executor re-settles a state "
                "by replaying frames rather than windows"
            )
        case CachePolicy.KEYED:
            raise AssertionError(f"{spec.tool_id} is cacheable; there is no refusal to explain")


def _digest(positions: tuple[str, ...], *parts: object) -> str:
    """Hash a declared list of JSON-representable parts.

    A JSON array rather than a delimiter join, so that no part can impersonate a
    boundary: a tool id containing whatever character was chosen as a separator
    would otherwise let two different inputs produce one string. The arity is
    fixed per key flavour and the positions are meaningful, so an absent input
    is `None` in place rather than a shorter list.

    Raises:
        AssertionError: if `parts` does not fill `positions`. The layout is a
            declaration rather than a description, and an unannounced part is
            the edit that turns the whole store over without saying so.
    """
    if len(parts) != len(positions):
        raise AssertionError(
            f"{len(positions)} positions {positions} were declared but {len(parts)} parts were "
            "handed to the digest"
        )
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


def source_key(source: str, *, decode_format: CropFormat) -> str:
    """The key for frames as the graph sees them: the ancestor of every root.

    `decode_format` is what the reader was opened in, and it belongs here for
    the same reason `decoder_identity()` does: it changes the pixel values every
    root is handed. A graph that reads no chroma is decoded from the luma plane
    rather than from a colour conversion of it (`decode/reader.py`), and the two
    are not the same array — so a colour graph and a luma graph over one file
    must not collide. `Dag.needs_chroma` derives it; nothing chooses it by hand,
    which is what stops the key and the reader disagreeing. It has no default
    for that reason: the caller that has not asked the graph has not answered
    this question either.

    Note what it is *not*: it is not the fact that this package's decode policy
    changed when the luma path landed. That is every entry ever computed, it is
    not per-run, and it is `DECODE_POLICY_VERSION` inside `decoder_identity()`.
    This position distinguishes two runs on one build; that constant
    distinguishes two builds.

    **Whether a written crop exists does not appear here, and must not.** The
    way an artifact changes a key is by being passed a *different `source`*,
    computed from the artifact file itself — and since the substitution became a
    document edit it is not even this function's caller who does it: a written
    crop is a source root over its own file, so what reaches here is that file's
    identity through the ordinary walk. This function is never asked "is there a
    crop"; it is handed footage, and an artifact is footage (`CropRecord`). A
    presence test in here would be a storage decision wearing a semantic
    decision's clothes.

    Args:
        source: What identifies the footage — `source_identity` builds one.
        decode_format: Which plane the reader was opened on, spelt as the
            document spells it (`CropFormat`).
    """
    return _digest(SOURCE_KEY_POSITIONS, "source", source, decoder_identity(), decode_format)


def picked_key(identity: str) -> str:
    """The key for a file a source tool reads: the ancestor of that one root.

    `source_key`'s sibling, and the whole reason there are two. A graph-fed
    root's ancestry is the footage the run decodes, so what identifies it is the
    file *and* the reader that opened it. A tool reading with *its own code* has
    nothing upstream to constrain it, so the reading is already covered by the
    `tool_id` and `version` positions of the node key below — `version` stands
    proxy for a tool's reading exactly as it does for its computing. Folding
    `decoder_identity()` and a decode format in anyway would key a picked PNG
    against the video decoder that never touched it, and would move every such
    key on the day `decode/` changes a seek strategy.

    Which is why this is not every source tool's key.
    `adr/a-root-keys-by-its-reader.md` rules the flavour off the reader: a
    source tool that opens its file through `decode/` is decoded by the same
    stack, in the same format, as the footage it stands in for, and folds
    `source_key` — so a written crop wired in at a crop node's place keys as
    that file's own footage would and moves nothing below it. `ToolSource.
    decoded` is the declaration; `Dag.node_keys` is the one reader of it.

    What it must do is move when the file moves, and that is the failure ADR-18
    names: get this wrong and swapping one background for another is invisible
    to the store, which serves the first model's results under the second's name
    — well-formed key, plausible frame, no symptom.

    **The rule that found the file is not in here, and not in the node below it
    either.** What is hashed is the resolved file's identity and never the
    pattern, so two projects naming one file agree about it
    (`adr/a-users-file-wires-in-like-any-other-input.md`). The pattern is still a
    parameter — saved, deviated per replicate, and what `ToolSource.file`
    resolves — but `node_key` drops it from the digest for that clause's sake,
    which is where the argument for the exclusion is written.

    The clause's other half, one project agreeing with itself after the folder is
    reorganized underneath it, is not this function's to give: `identity` is
    `source_identity`'s three facts and the first of them is the resolved
    absolute path, so footage that moved is a new identity by that function's own
    argument.

    Args:
        identity: What identifies the picked file — `source_identity` builds
            one, from the path the tool's own resolution came back with.
    """
    return _digest(PICKED_KEY_POSITIONS, "picked", identity)


def node_key(
    node: Node,
    *,
    spec: ToolSpec,
    upstream: Sequence[tuple[str | None, str]],
    replicate: Replicate | None = None,
) -> str:
    """The key for `node`'s output, for one replicate.

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

    **A path parameter is the one parameter that does not.** `spec.path_params`
    are dropped from the params position, and this is the module's "nothing that
    cannot change the bytes may be" read strictly rather than an exception to it:
    the file such a parameter names is already in this key, as the identity
    folded into the `upstream` pair a source root arrives on (`picked_key`,
    `source_key`), so what the parameter would add is the *rule that found the
    file* and nothing else. `adr/a-users-file-wires-in-like-any-other-input.md`
    forbids that rule by name, and the case is `test_cache_key.TestPortability`:
    `resolve_source.anchored` rewrites a relative path against the project's own
    directory before anything is keyed, so leaving it in put the folder holding
    the project file inside every key below its source, and two projects naming
    one background disagreed about it.

    Scoped by `path_params` alone rather than by asking whether the spec is a
    source tool, because `ToolSpec._check_source` refuses a path parameter on a
    tool with nothing that opens it — the two are one declaration, so a second
    test for it here could only ever disagree with the first. What this does
    assume is that every path parameter a source declares names a file whose
    identity reaches `picked`: a source tool that read a *second* file, from a
    second path parameter, would drop that file out of its key entirely, and the
    walk that builds `picked` has the same gap for the same reason
    (`resolve_source.source_files` resolves one file per root).

    Args:
        node: The graph node. Its `tool_id` and `version` must match `spec`.
        spec: The registered tool, resolved by the caller — `dag.py` does this
            against a `ToolRegistry` and the executor carries the result.
        upstream: `(port, key)` for every node feeding this one, which for a
            root is one pair on `SOLE_PORT` carrying the `source_key` of the
            footage or the `picked_key` of the file the tool reads. Ordered, and
            the caller owns the order: `Dag.inputs` sorts by port, so writing
            two edges the other way round is one graph and one key, while
            crossing which parent feeds which port is two of each — `a - b` and
            `b - a` are fed by the same two keys and are not the same
            computation.
        replicate: The replicate being processed; `None` for the node's
            baseline, which is what a project with no fan-out runs.

    Raises:
        NotCacheableError: if `spec` may not be keyed under `cache_policy`.
        ValueError: if `spec` describes a different tool than `node` names.
        ValidationError: if the resolved parameters are not valid for
            `spec.params_model` — a misspelled key, or a value out of range.
    """
    if spec.key != (node.tool_id, node.version):
        raise ValueError(
            f"spec is {spec.tool_id} {spec.version} but node names {node.tool_id} {node.version}"
        )
    if not is_cacheable(spec):
        raise NotCacheableError(
            f"{spec.tool_id} {spec.version} {_uncacheable_clause(spec)} — nothing that reads "
            "such an entry can know it matches what would be recomputed"
        )
    params = spec.params_model.model_validate(resolved_params(node, replicate))
    return _digest(
        NODE_KEY_POSITIONS,
        "node",
        # A list of two-element lists once JSON has been through it, which is
        # what keeps a port from being able to impersonate a key: the pairing is
        # structural rather than a separator inside one string.
        [[port, key] for port, key in upstream],
        node.tool_id,
        node.version,
        params.canonical_json(without=spec.path_params),
    )
