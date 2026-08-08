"""The derived docs: indexes, ARCHITECTURE, the scaffold, and `--next`.

Work items: one file each, YAML frontmatter, two shapes. A *sequenced* item
carries `step:` — dotted numbers whose first component is the phase, so
"02.3.1" is an aside inserted between "02.3" and "02.4" without renumbering
anything. A *pool* item carries `priority:` instead — work noticed while doing
the phase rather than committed to by it.

The order over both is one sort key (`queue_key`) and there is no state in it:
phase, then a step before a pool item, then the number or the priority, then
the name. So `--next` is the first `open` row of `docs/todo/.index.md` read top
to bottom, and a reader who scrolls to it lands on the item the loop is about
to take — asserted, not promised. The queue that runs the work never has to
encode an order; the repo holds it.

Phase outranks urgency, which is the whole of what makes it simple: an earlier
phase is groundwork the later ones stand on, so a `low` in phase 0 precedes a
`high` in phase 5. Work that cannot wait for its phase is not a pool item at
all — it is minted as a decimal step in the phase's own list, and a phase whose
steps all read `done` is still a place to file one.

Either shape may declare its own arithmetic, and both declarations are refused
where they disagree with what they stand over: `table_rows:` against the body
rows of the item's own markdown tables, and `cases:` — a v3 test file mapped to
the number of cases it holds — against that file. A re-derivation item states
both in prose, and the prose totals are the one part of such an item nothing
reaches, which is why they have been wrong three times over tables whose
verdict columns were exact
(`findings/loop/2026.08.07-the-run-that-corrected-an-inherited-miscount-wrote-its-own.md`).

Findings: one file per measurement, newest first, `verdict` standing alone as
the row a reader triages from. `docs/findings/loop/` holds the same shape for
truths about how the work loop fails rather than about the system — separate
folder because the audiences never overlap: loop findings are what the review
prompt is distilled from.

ADRs: one short file per settled decision under `docs/adr/`, and
`docs/ARCHITECTURE.md` is their index. The `adr:` number is identity — minted
once, never reused, citable as "ADR-7" — while `position:` is placement only:
dotted two-digit pairs whose first pair names a `_GROUPS.md` group and each
further pair indents one level, freely rewritable as the shelf is rearranged.
A superseded ADR keeps its number and its file but surrenders its position,
so the index shows only what still binds and never goes stale. The index line
is the ADR body's first paragraph — same trick as the scaffold, so it cannot
drift from the file. An ADR records a decision that outlives the text that
made it; a claim a contract or test already checks is cited, not minted.

The scaffold: `docs/SCAFFOLD.md` answers "where does this module go", derived
from each module docstring's first line rather than maintained by hand —
v2's SCAFFOLD annotation was a hand-kept copy of exactly that line, and a
declared copy of derivable state drifts. The one half that cannot be derived
is intent: `FORBIDDEN` names the paths the plan dropped, checked must-not-
exist, because a dropped module that quietly gets built is the drift the
scaffold exists to catch. Deriving proves the annotation reached the tree
intact and cannot prove it says what VISION.md's component table gives the
package, so `annotation_gaps` checks that second link against the bold spans
in the table's "Owns" cells.

Everything generated here is derived, never edited, and
`tests/docs/test_doc_index.py` fails when any of it drifts from the files it
describes — v2's discipline, cut to the subset v3 uses (no primer, no settled
table, no `after:` graph; the step numbers are the ordering those existed to
compute).

The four have four separate sources and share only the list in `derived`, so a
run writes every target that renders and reports every one that does not. What
this refuses is the shape where they were rendered together: one docstring over
the annotation limit refused SCAFFOLD.md and left the other three stale, and
`--next` — which reads the items and no docstring at all — stopped answering
with them, so the loop could not take the item that would have recorded it.

    uv run python scripts/doc_index.py           # rewrite everything generated
    uv run python scripts/doc_index.py --check   # exit 1 if anything is stale
    uv run python scripts/doc_index.py --next    # the next role and its item
    uv run python scripts/doc_index.py --mint X  # start item X, refusing a taken slug

Minting goes through the tool because a slug is an identity and writing one
directly is how an item gets deleted: the write succeeds, the index rebuilds
from whatever files exist, and nothing is red. `tracked_drift` catches the
sessions that write anyway, by the `opened` date a replaced item cannot keep.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
TODO_DIR = REPO / "docs" / "todo"
FINDINGS_DIR = REPO / "docs" / "findings"
LOOP_DIR = FINDINGS_DIR / "loop"
PLAN = REPO / "docs" / "PLAN.md"
SCAFFOLD = REPO / "docs" / "SCAFFOLD.md"
ADR_DIR = REPO / "docs" / "adr"
GROUPS = ADR_DIR / "_GROUPS.md"
ARCHITECTURE = REPO / "docs" / "ARCHITECTURE.md"
INDEX_NAME = ".index.md"

#: Where modules live; anything else in the repo carries no docstring to read.
SCAN_ROOTS = ("src", "scripts")

#: The half of the scaffold that cannot be derived: intent. These are the
#: paths PLAN.md's disposition dropped, and a dropped module that quietly gets
#: built is the drift the scaffold exists to catch — so their absence is a
#: gate, not a comment. Shrink-or-grow only with the plan.
FORBIDDEN = (
    "src/sieve/backend",
    "src/sieve/detect",
    "src/sieve/workers",
    "src/sieve/gui/filter_tab.py",
)

#: The stack top-down, so the scaffold reads in import order: a package may
#: reach only what is listed below it. `.importlinter`'s layers contract is the
#: authority and this tuple follows it — a package added there is added here in
#: the same commit, or the scaffold renders an order the linter does not check.
LAYER_ORDER = (
    "gui",
    "cli",
    "bench",
    "pipeline",
    "tools",
    "decode",
    "storage",
    "mutual",
    "core",
)

#: ADR-6 (`adr/core-membership-is-closed.md`): core owns exactly these, and a
#: new direct child is a revision of that ADR — refused here until it is made.
CORE_CHILDREN = (
    "__init__.py",
    "types.py",
    "tool_base.py",
    "tool_registry.py",
    "pipeline_model.py",
    "ops",
)

#: VISION.md's component table is where a package's ownership is decided, and
#: the `__init__.py` first line is where it is stated. The cell is prose with
#: links and qualifications in it and stays prose; what makes it readable is
#: that the *enumeration* inside it is marked — every `**bold**` span is a
#: thing the package owns and has to name. Marking is a person's call when the
#: row is written, so what the gate proves is that the line names everything
#: marked, not that the row marked everything the sentence meant.
COMPONENT_HEADING = "## Components, and what each must never own"
COMPONENT_ROW = re.compile(r"^\|\s*`(?P<package>[a-z_]+)`\s*\|(?P<owns>[^|]*)\|")
OWNED = re.compile(r"\*\*(.+?)\*\*")

#: ADR-16 (`adr/annotation-limit-is-the-source-line-budget.md`): the limit is
#: the docstring line's own budget — ruff's 100 columns less the opening
#: `"""` — so any first line that fits v3 source fits here, and what the gate
#: still refuses is a paragraph in the cell.
ANNOTATION_LIMIT = 97
BANNED_IN_ANNOTATION = ("helper", "utils", "utility", "various", "miscellaneous", "this module")

#: `_TEMPLATE.md` and the generated index itself are machinery, not entries.
SKIP_PREFIXES = ("_", ".")

NOTICE = "<!-- Generated by scripts/doc_index.py. Do not edit; rerun the tool. -->"

#: `awaiting-review` sits between the worker's claim and the reviewer's
#: verdict: a worker may move an item open -> awaiting-review and no further,
#: so "done" is always someone else's edit — checkable in the item's diff.
STATUSES = ("open", "awaiting-review", "deferred", "done")
PRIORITIES = ("high", "normal", "low", "unassessed")

#: The items that already exist without a criterion, and the only ones allowed
#: to. **Shrink-only**: a name leaves when the item gets its `done_when` and
#: nothing may be added, which is what makes the rule bind on new items while
#: the backlog is paid down rather than deleted.
#:
#: The hole this closes was open from `2118751`, the commit that created the
#: folder: `validate` asked for a criterion when an item carried a `step` and
#: asked nothing of a pool item. Forty-nine accumulated. The loop then grew a
#: `specify` role (`e31fbeb`) to write them after the fact, which drains the
#: debt and is why `--next` still routes to it — but a role that pays a cost
#: is not a reason to keep incurring it, and an item whose completion the
#: session doing it gets to define is the same defect off-step as on it.
#:
#: `tests/docs/test_doc_index.py` holds the ratchet: every name here must
#: still exist and still lack a criterion, so an entry that has been repaid
#: fails until it is removed.
UNSPECIFIED_DEBT = frozenset(
    {
        "a-budget-miss-is-an-exit-code-once-something-can-force-one.md",
        "a-checkpoint-does-not-record-which-product-it-holds.md",
        "a-composite-parameter-prints-no-shape-and-no-bounds.md",
        "a-declared-lag-whose-only-reader-is-its-own-test.md",
        "a-detector-cannot-run-to-the-end-of-its-own-footage.md",
        "a-merge-keys-its-inputs-by-port.md",
        "a-node-id-reaches-the-filesystem-with-no-spelling-rule.md",
        "a-per-replicate-setting-is-asserted-against-the-whole-document.md",
        "a-record-survives-the-rename-it-is-built-to-survive.md",
        "a-run-commits-what-it-wrote.md",
        "an-unattached-item-is-owed-everywhere-and-ordered-last.md",
        "awaiting-review-returns-to-the-selection-rule.md",
        "block-signal-refuses-and-converts-with-no-case.md",
        "crop-bindings-helper-clauses-have-no-case.md",
        "cut-to-ready-gets-a-headless-referent.md",
        "detects-degenerate-branches-and-its-validator-get-cases.md",
        "four-checkpoint-writer-refusals-have-no-case.md",
        "inspects-selector-line-is-asserted-by-a-substring-of-the-tool-id.md",
        "per-tool-documents-are-decided-or-dropped.md",
        "previews-replicate-store-and-fallbacks-are-declared-and-not-asserted.md",
        "temporal-baseline-pins-its-degenerate-paths.md",
        "the-admission-argument-is-retold-in-four-modules.md",
        "the-aperture-cutoff-holds-a-hundredfold-mutation.md",
        "the-detect-parity-target-is-named.md",
        "the-dilation-radius-runs-only-at-its-clamp.md",
        "the-first-gui-cut-names-its-surfaces.md",
        "the-narrowing-case-cannot-see-what-it-did-not-ask-for.md",
        "the-non-finite-guards-get-the-case-their-subject-needs.md",
        "the-offering-predicate-is-not-the-edge-legality-check.md",
        "the-read-back-shape-check-has-no-case.md",
        "the-review-has-a-path-for-a-partial-deferral.md",
        "the-rss-floor-decides-its-fate.md",
        "the-second-failing-command-moves-the-shared-refusals.md",
        "two-items-name-the-same-crop-artifact-test-file.md",
    }
)

#: Why a deferral is a deferral, typed so the set can be triaged by machine
#: while `gated_on` keeps the sentence saying which decision, which subject,
#: which phase. All three are blocks outside the item: no session can clear
#: one, which is why a deferred item is not in the queue at all.
#:
#: There is deliberately no reason for "has no `done_when` yet". That is not a
#: block, it is minting the session did not finish, and a legal deferral for it
#: is where every item anybody found hard would go. Unspecified is derived from
#: the absent field (`unspecified`), never declared, and it costs a `specify`
#: run at the head of the queue rather than a place outside it.
DEFER_REASONS = (
    "decision",  # only Kendrick can settle it
    "subject",  # the thing it would be about does not exist yet
    "phase",  # no phase hosts it yet; pulled in when one is minted
)

#: An ADR is `settled` or it is `superseded` — there is no `proposed`, because
#: a decision is minted when it has been made, not to make it.
ADR_STATUSES = ("settled", "superseded")

#: Placement on the shelf: two-digit pairs, group first, one indent per
#: further pair. Freely rewritable — identity lives in `adr:`, never here.
ADR_POSITION = re.compile(r"^\d{2}(\.\d{2})+$")
GROUP_LINE = re.compile(r"^(\d{2}) — (.+?)\s*$", re.MULTILINE)

#: The index line is the body's first paragraph: the decision in a sentence
#: or two, not the rationale.
ADR_SUMMARY_LIMIT = 200

#: A finding is `closed` when the code reflects it, `open` when measured but
#: not yet acted on, `superseded` when a later finding names it in
#: `supersedes:` — the file stays, because a record of what was believed is
#: the reason the code took the shape it did.
FINDING_STATUSES = ("closed", "open", "superseded")

#: At least two components: the first is the phase, so a bare "2" would be an
#: item claiming a phase and no place in it.
STEP = re.compile(r"^\d+(\.\d+)+$")
PHASE_HEADING = re.compile(r"^## Phase (\d+) — (.+?)\s*$", re.MULTILINE)

#: Where an item with no phase sorts: after every phase there is. Chosen rather
#: than derived, and it is the open question in
#: `todo/an-unattached-item-is-owed-everywhere-and-ordered-last.md` — repo-wide
#: work is owed everywhere, which is as good an argument for first as for last.
UNPHASED = 1 << 16

#: The literal for "not gated". Spelled out and required so an ungated item is
#: a decision somebody made, not a field somebody skipped.
UNGATED = "nothing"

#: What a slug may be made of. Narrow on purpose: the folder is the identity
#: space, and two spellings differing only by case are one file on Windows, so
#: a rule admitting them would let a mint collide on one platform and not on
#: the machine that wrote the check.
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

#: A markdown table's second line, which is what tells a run of pipe lines from
#: a table: rows are the run less its header and this.
TABLE_RULE = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+$")

#: The one frontmatter field written at mint and never edited afterwards, which
#: is what makes it the witness that a slug was reused: everything else about an
#: item is expected to move.
OPENED = re.compile(r"^opened:\s*(\S+)\s*$", re.MULTILINE)


#: The nearest mapping key at or above a scanner stop, which is the field whose
#: value it was in the middle of. Leading `-` so a key inside a list entry
#: (`- probe:`) answers as itself rather than as the list it is in.
YAML_KEY = re.compile(r"^\s*(?:-\s+)?(?P<key>[A-Za-z_][\w-]*)\s*:")


class ItemError(ValueError):
    """An item file that cannot be indexed as written."""


@dataclass(frozen=True)
class Item:
    path: Path
    fields: dict[str, Any]

    @property
    def step_key(self) -> tuple[int, ...] | None:
        raw = self.fields.get("step")
        if raw is None:
            return None
        return tuple(int(part) for part in str(raw).split("."))

    @property
    def phase(self) -> int | None:
        key = self.step_key
        if key is not None:
            return key[0]
        raw = self.fields.get("phase")
        return int(raw) if raw is not None else None

    @property
    def status(self) -> str:
        return str(self.fields.get("status", ""))

    @property
    def priority_rank(self) -> int:
        value = str(self.fields.get("priority", ""))
        return PRIORITIES.index(value) if value in PRIORITIES else len(PRIORITIES)


def _yaml_blame(body: list[str], error: yaml.YAMLError) -> str:
    """Why the frontmatter would not parse, as a line in the file and a field.

    PyYAML reports the stop as a position inside the string it was handed, in a
    stream it calls `<unicode string>`, so an author is told which character
    offended and left to find it — and the commonest way to reach here is a
    value opening with a code span, where the character named is a backtick the
    file is full of. Both halves are recoverable: the frontmatter body starts at
    file line 2, and the field is the nearest key at or above the stop.
    """
    mark = getattr(error, "problem_mark", None)
    if mark is None:
        return f"frontmatter is not valid YAML — {error}"
    where = f"line {mark.line + 2}"
    for line in reversed(body[: mark.line + 1]):
        key = YAML_KEY.match(line)
        if key:
            where += f", `{key['key']}`"
            break
    problem = getattr(error, "problem", None) or "will not parse"
    context = getattr(error, "context", None)
    return f"frontmatter is not valid YAML at {where} — " + (
        f"{context}, {problem}" if context else problem
    )


def parse_frontmatter(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ItemError(f"{path.name}: no frontmatter — the file must open with `---`")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        raise ItemError(f"{path.name}: frontmatter is never closed with `---`") from None
    try:
        loaded: object = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as error:
        raise ItemError(f"{path.name}: {_yaml_blame(lines[1:end], error)}") from error
    if not isinstance(loaded, dict):
        raise ItemError(f"{path.name}: frontmatter must be a mapping")
    return {str(key): value for key, value in loaded.items()}


def table_rows(body: str) -> int:
    """Body rows across every markdown table in `body`.

    Every table, summed, because an item's total stands over its whole
    enumeration and 03.6 split one across two headings. A run of pipe lines
    with no rule under it is not a table and counts nothing — which fails a
    declaration loudly rather than passing it on a table markdown never read.
    """
    total, fenced, run = 0, False, []

    def close(run: list[str]) -> int:
        return len(run) - 2 if len(run) > 1 and TABLE_RULE.match(run[1]) else 0

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
        if fenced or stripped.startswith("```"):
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            run.append(stripped)
            continue
        total += close(run)
        run = []
    return total + close(run)


def case_count(path: Path) -> int:
    """Test functions in `path`, at module level or inside a class."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name.startswith("test_")
    )


def check_totals(path: Path, fields: dict[str, Any]) -> None:
    """The two totals an item may state about itself, against their subjects.

    The tree the `cases:` paths are read against is two folders above the item,
    because an item's home is `<repo>/docs/todo` — so a fixture repo is checked
    the same way this one is, rather than the check being live in one of them.

    A path with no file yet is skipped rather than refused: the count is stated
    when the item is written and the test file is what the item goes on to
    write, so demanding it exist would make the item unindexable until it was
    finished. At `done` the check stops entirely — by then the number is a
    record of what the item delivered, and later items add cases to the same
    file, so holding a finished item to it would pin every test file's size to
    whatever the item that created it found.
    """
    declared = fields.get("table_rows")
    if declared is not None:
        if not isinstance(declared, int):
            raise ItemError(f"{path.name}: `table_rows` must be a bare number")
        _, _, body = path.read_text(encoding="utf-8").partition("\n---\n")
        held = table_rows(body)
        if held != declared:
            raise ItemError(f"{path.name}: says {declared} rows over tables holding {held}")

    cases = fields.get("cases")
    if cases is None or str(fields.get("status", "")) == "done":
        return
    if not isinstance(cases, dict):
        raise ItemError(f"{path.name}: `cases` maps a test file to the number of cases it holds")
    repo = path.resolve().parents[2]
    for relative, stated in cases.items():
        if not isinstance(stated, int):
            raise ItemError(f"{path.name}: `cases` value for {relative} must be a bare number")
        named = repo / str(relative)
        if not named.is_file():
            continue
        held = case_count(named)
        if held != stated:
            raise ItemError(f"{path.name}: says {relative} holds {stated} cases; it holds {held}")


def validate(path: Path, fields: dict[str, Any]) -> None:
    for key in ("title", "status", "opened", "gated_on"):
        if not str(fields.get(key, "")).strip():
            raise ItemError(f"{path.name}: missing `{key}`")
    if fields["status"] not in STATUSES:
        raise ItemError(f"{path.name}: status {fields['status']!r} is not one of {STATUSES}")
    if fields["status"] == "deferred":
        if str(fields["gated_on"]).strip() == UNGATED:
            raise ItemError(f"{path.name}: deferred with `gated_on: {UNGATED}` is not a deferral")
        if fields.get("deferred_for") not in DEFER_REASONS:
            raise ItemError(f"{path.name}: a deferral needs `deferred_for` from {DEFER_REASONS}")
    elif "deferred_for" in fields:
        raise ItemError(f"{path.name}: `deferred_for` on an item that is not deferred")

    step = fields.get("step")
    if step is not None:
        if not STEP.match(str(step)):
            raise ItemError(f"{path.name}: step {step!r} is not dotted numbers (phase first)")
        if not str(fields.get("done_when", "")).strip():
            raise ItemError(f"{path.name}: a sequenced item needs `done_when`")
        if "priority" in fields:
            # The number is the ordering; a priority beside it is a second
            # ordering, and two orderings is how a list stops having one.
            raise ItemError(f"{path.name}: a sequenced item takes no `priority`")
        if "phase" in fields:
            raise ItemError(f"{path.name}: phase is the step's first component; drop `phase`")
    else:
        if fields.get("priority") not in PRIORITIES:
            raise ItemError(f"{path.name}: a pool item needs `priority` from {PRIORITIES}")

    # Last, so a malformed item is reported on its shape first. Every item
    # carries its criterion; the one exemption is a deferral on a decision,
    # where what the command would assert is the thing being decided, so
    # writing one now is this session guessing the answer. It is owed the
    # moment the deferral lifts, since `open` is not exempt — the other half
    # of the guard above refusing `deferred_for` on an item that is not
    # deferred, which is what stops the exemption being worn by live work.
    if (
        not str(fields.get("done_when", "")).strip()
        and fields.get("deferred_for") != "decision"
        and path.name not in UNSPECIFIED_DEBT
    ):
        raise ItemError(
            f"{path.name}: an item needs `done_when` — the criterion is written when the "
            f"item is written, by someone other than whoever will satisfy it"
        )

    check_totals(path, fields)


def collect(todo_dir: Path = TODO_DIR) -> list[Item]:
    items: list[Item] = []
    for path in sorted(todo_dir.glob("*.md")):
        if path.name.startswith(SKIP_PREFIXES):
            continue
        fields = parse_frontmatter(path)
        validate(path, fields)
        items.append(Item(path=path, fields=fields))
    return items


def mint(slug: str, todo_dir: Path = TODO_DIR) -> Path:
    """Start `<slug>.md` from the template, refusing a name already taken.

    What this closes is not a wrong item but a *missing* one. A session mints by
    writing a slug, and a write to a slug something already holds replaces that
    item's body wholesale with nothing going red, because the index is rebuilt
    from whatever files exist — a replaced item is exactly as consistent with
    the index as an untouched one. The repo keeps one copy of its memory of
    noticed work.

    Refusing at mint time is the half that fixes the class rather than
    reporting it: a session that has to ask for a name cannot take one by
    accident. `tracked_drift` is the net under the sessions that do not ask.

    Existence is tested against the folder listing case-folded as well as
    through the path, because NTFS answers this one way and the index another.

    Raises:
        ItemError: if `slug` is not a slug, or the folder already holds it.
    """
    if not SLUG.match(slug):
        raise ItemError(f"{slug!r} is not a slug: lowercase words joined by single hyphens")
    taken = {path.name.casefold(): path.name for path in todo_dir.glob("*.md")}
    clash = taken.get(f"{slug}.md".casefold())
    if clash is not None:
        raise ItemError(
            f"{clash} already exists — minting over it would delete an item and leave the index "
            f"consistent. Pick another slug, or edit that item if it is the same work."
        )
    path = todo_dir / f"{slug}.md"
    path.write_text((todo_dir / "_TEMPLATE.md").read_text(encoding="utf-8"), encoding="utf-8")
    return path


def _git(*args: str, repo: Path = REPO) -> str | None:
    """`git` in `repo`, or `None` when it cannot answer.

    `None` rather than an exception for every way the question is unavailable —
    no git on PATH, no commits yet, a tree unpacked from an archive — so that a
    check meant to catch a lost item never becomes the reason the index will
    not build.
    """
    try:
        finished = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return finished.stdout


def tracked_drift(todo_dir: Path = TODO_DIR, repo: Path = REPO) -> list[str]:
    """Items the folder has lost or overwritten since the last commit.

    Two symptoms of one accident. A tracked item whose file is gone is the
    plain case; a tracked item whose `opened` has moved is the case that
    motivated this, because a mint over an occupied slug leaves behind a file
    that is perfectly valid and is a different item than the one committed.

    The finding says "moves backwards" and this checks for a move in either
    direction, which is a correction rather than a widening: a collision stamps
    *today*, so the date it writes goes forward, and a rule reading one
    direction would miss the accident that actually happened. `opened` is
    written once and never edited, so any move is the same evidence.

    Both messages name the recovery, because both are survivable until someone
    commits over them: the body that was replaced is still in `HEAD`.
    """
    try:
        folder = todo_dir.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        # A folder outside the repo has no committed half to have drifted from.
        return []
    listing = _git("ls-files", "-z", "--", folder, repo=repo)
    if not listing:
        return []
    # One `git grep` for every committed `opened:` rather than a `git show` per
    # item: the second shape is a subprocess per file, which on this platform
    # costs most of a second for a folder this size, paid by every session.
    blobs = _git(
        "grep", "-I", "-n", "--no-color", "-e", "^opened:", "HEAD", "--", folder, repo=repo
    )
    was: dict[str, str] = {}
    for line in (blobs or "").splitlines():
        # `HEAD:docs/todo/<slug>.md:<lineno>:opened: <date>`. The first hit in a
        # file is the frontmatter's; a later one would be prose quoting it.
        _, _, rest = line.partition(":")
        relative, _, tail = rest.partition(":")
        _, _, value = tail.partition("opened:")
        was.setdefault(relative, value.strip())

    problems: list[str] = []
    for relative in sorted(filter(None, listing.split("\0"))):
        name = relative.rsplit("/", 1)[-1]
        if not name.endswith(".md") or name.startswith(SKIP_PREFIXES):
            continue
        path = repo / relative
        if not path.exists():
            problems.append(f"{name} is tracked and gone from the folder; it is still in HEAD")
            continue
        before = was.get(relative)
        found = OPENED.search(path.read_text(encoding="utf-8"))
        after = found.group(1) if found else None
        if before and after and before != after:
            problems.append(
                f"{name}: `opened` moved {before} -> {after}, which it never does — the slug was "
                f"written over. `git show HEAD:{relative}` is the item that was there"
            )
    return problems


def phase_titles(plan: Path = PLAN) -> dict[int, str]:
    """Phase number -> title, read from PLAN.md's headings — the one home."""
    if not plan.is_file():
        return {}
    return {int(n): title for n, title in PHASE_HEADING.findall(plan.read_text(encoding="utf-8"))}


def _cell(value: object) -> str:
    return " ".join(str(value if value is not None else "").split()).replace("|", "\\|")


def _table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def render(items: list[Item], titles: dict[int, str]) -> str:
    lines = [
        NOTICE,
        "",
        "# Work items",
        "",
        "One file per item; phases are `PLAN.md`'s. The next thing the loop",
        "does is the first `open` row on this page, read top to bottom — the",
        "tables below are laid out in the order `--next` selects in, and",
        "`tests/docs/test_doc_index.py` fails if the two ever disagree. A",
        "worker moves an item to `awaiting-review`, a review to `done`.",
        "",
    ]
    if not items:
        lines.append("*No items yet. Copy `_TEMPLATE.md` to `<slug>.md`.*")
        return "\n".join(lines) + "\n"

    phases = sorted({item.phase for item in items if item.phase is not None})
    for phase in phases:
        title = titles.get(phase, "")
        lines.append(f"## Phase {phase}" + (f" — {title}" if title else ""))
        lines.append("")
        sequenced = sorted(
            (i for i in items if i.phase == phase and i.step_key is not None),
            key=lambda i: i.step_key or (),
        )
        if sequenced:
            lines += _table(
                ("Step", "Status", "Item", "Gated on"),
                [
                    (
                        str(item.fields.get("step")),
                        item.status,
                        f"[{_cell(item.fields.get('title'))}]({item.path.name})",
                        _cell(item.fields.get("gated_on")),
                    )
                    for item in sequenced
                ],
            )
            lines.append("")
        pooled = sorted(
            (i for i in items if i.phase == phase and i.step_key is None),
            key=lambda i: (i.priority_rank, i.path.name),
        )
        if pooled:
            lines += ["Asides that can wait:", ""]
            lines += _table(
                ("Priority", "Status", "Item", "Gated on"),
                [
                    (
                        _cell(item.fields.get("priority")),
                        item.status,
                        f"[{_cell(item.fields.get('title'))}]({item.path.name})",
                        _cell(item.fields.get("gated_on")),
                    )
                    for item in pooled
                ],
            )
            lines.append("")

    unattached = sorted(
        (i for i in items if i.phase is None), key=lambda i: (i.priority_rank, i.path.name)
    )
    if unattached:
        lines += ["## Unattached", ""]
        lines += _table(
            ("Priority", "Status", "Item", "Gated on"),
            [
                (
                    _cell(item.fields.get("priority")),
                    item.status,
                    f"[{_cell(item.fields.get('title'))}]({item.path.name})",
                    _cell(item.fields.get("gated_on")),
                )
                for item in unattached
            ],
        )
        lines.append("")

    lines += _render_waiting(items)

    open_count = sum(1 for item in items if item.status == "open")
    lines.append(f"*{len(items)} items, {open_count} open.*")
    return "\n".join(lines) + "\n"


def waiting_on_kendrick(items: list[Item]) -> tuple[list[Item], list[Item]]:
    """A deferral nothing can clear, and a pool item with no criterion yet.

    Grouped because from the outside they are one question — what is not going
    to move on its own. They differ in who moves them, and only the first is
    strictly a person: an unspecified item is the head of the queue's problem
    the moment it reaches the front, and `next_action` sends a `specify` run at
    it. What the table is for is the count, which is the size of the debt
    between here and a queue that runs without stopping to define itself.
    """
    deferred = sorted((i for i in items if i.status == "deferred"), key=queue_key)
    unspecified_items = sorted(
        (
            i
            for i in items
            if i.status == "open"
            and i.step_key is None
            and not str(i.fields.get("done_when", "")).strip()
        ),
        key=queue_key,
    )
    return deferred, unspecified_items


def _render_waiting(items: list[Item]) -> list[str]:
    deferred, unspecified_items = waiting_on_kendrick(items)
    if not deferred and not unspecified_items:
        return []
    lines = [
        "## Waiting on a person",
        "",
        "A deferral is blocked outside the item and no session can clear it.",
        "An unspecified item is not blocked — it becomes a `specify` run when",
        "it reaches the head of the queue — but it costs a session before it",
        "costs any work, so the length of the second table is how far the",
        "queue is from running without stopping to define itself. That table",
        "only shrinks: an item now needs its `done_when` to validate at all,",
        "so the ones below are the backlog from before the rule and nothing",
        "joins them (`UNSPECIFIED_DEBT` in `scripts/doc_index.py`).",
        "",
    ]
    if deferred:
        lines += _table(
            ("Reason", "Phase", "Item", "Gated on"),
            [
                (
                    _cell(item.fields.get("deferred_for")),
                    _cell(item.phase),
                    f"[{_cell(item.fields.get('title'))}]({item.path.name})",
                    _cell(item.fields.get("gated_on")),
                )
                for item in deferred
            ],
        )
        lines.append("")
    if unspecified_items:
        lines += ["No `done_when`, so each costs a `specify` run first:", ""]
        lines += _table(
            ("Priority", "Phase", "Item"),
            [
                (
                    _cell(item.fields.get("priority")),
                    _cell(item.phase),
                    f"[{_cell(item.fields.get('title'))}]({item.path.name})",
                )
                for item in unspecified_items
            ],
        )
        lines.append("")
    return lines


def validate_finding(path: Path, fields: dict[str, Any]) -> None:
    for key in ("title", "date", "status", "verdict"):
        if not str(fields.get(key, "")).strip():
            raise ItemError(f"{path.name}: missing `{key}`")
    if fields["status"] not in FINDING_STATUSES:
        raise ItemError(
            f"{path.name}: status {fields['status']!r} is not one of {FINDING_STATUSES}"
        )


def collect_findings(folder: Path) -> list[Item]:
    """Findings in `folder`, newest first — a reader arrives for the latest."""
    findings: list[Item] = []
    if not folder.is_dir():
        return findings
    for path in sorted(folder.glob("*.md")):
        if path.name.startswith(SKIP_PREFIXES):
            continue
        fields = parse_frontmatter(path)
        validate_finding(path, fields)
        findings.append(Item(path=path, fields=fields))
    findings.sort(key=lambda f: (str(f.fields["date"]), f.path.name), reverse=True)
    return findings


def _finding_rows(findings: list[Item], prefix: str = "") -> list[str]:
    return _table(
        ("Date", "Finding", "Status", "Verdict"),
        [
            (
                str(finding.fields["date"]),
                f"[{_cell(finding.fields.get('title'))}]({prefix}{finding.path.name})",
                finding.status,
                _cell(finding.fields.get("verdict")),
            )
            for finding in findings
        ],
    )


def render_findings(findings: list[Item], loop: list[Item]) -> str:
    lines = [
        NOTICE,
        "",
        "# Findings",
        "",
        "One file per measurement, newest first. `verdict` is the whole result —",
        "open the file for the method. A finding says what is *true about the",
        "system* and outlives the code that prompted it; a work item says what",
        "was built.",
        "",
    ]
    if findings:
        lines += _finding_rows(findings)
    else:
        lines.append("*No findings yet. Copy `_TEMPLATE.md` to `YYYY.MM.DD-short-name.md`.*")
    if loop:
        lines += [
            "",
            "## Loop",
            "",
            "Truths about how the work loop fails rather than about the system —",
            "what the review prompt is distilled from.",
            "",
        ]
        lines += _finding_rows(loop, prefix="loop/")
    lines += ["", f"*{len(findings) + len(loop)} findings.*"]
    return "\n".join(lines) + "\n"


def parse_groups(path: Path = GROUPS) -> dict[int, str]:
    """Group number -> title, from `_GROUPS.md` — the one home for the names."""
    if not path.is_file():
        return {}
    return {int(n): title for n, title in GROUP_LINE.findall(path.read_text(encoding="utf-8"))}


def validate_adr(path: Path, fields: dict[str, Any]) -> None:
    for key in ("title", "adr", "status", "decided"):
        if not str(fields.get(key, "")).strip():
            raise ItemError(f"{path.name}: missing `{key}`")
    if not isinstance(fields["adr"], int):
        raise ItemError(f"{path.name}: `adr` must be a bare number — it is the fixed identity")
    if fields["status"] not in ADR_STATUSES:
        raise ItemError(f"{path.name}: status {fields['status']!r} is not one of {ADR_STATUSES}")
    if fields["status"] == "settled":
        if not ADR_POSITION.match(str(fields.get("position", ""))):
            raise ItemError(
                f"{path.name}: a settled ADR needs `position` as dotted two-digit "
                f'pairs, group first ("02.01")'
            )
        if "superseded_by" in fields:
            raise ItemError(f"{path.name}: settled with `superseded_by` — pick one")
    else:
        if not str(fields.get("superseded_by", "")).strip():
            raise ItemError(f"{path.name}: superseded without `superseded_by` naming the successor")
        if "position" in fields:
            # Surrendering the position is what takes a dead decision off the
            # index; a superseded ADR that keeps one would still be shelved.
            raise ItemError(f"{path.name}: a superseded ADR holds no `position`")


def _position_key(item: Item) -> tuple[int, ...]:
    return tuple(int(part) for part in str(item.fields["position"]).split("."))


def collect_adrs(folder: Path = ADR_DIR, groups: dict[int, str] | None = None) -> list[Item]:
    groups = parse_groups() if groups is None else groups
    adrs: list[Item] = []
    if not folder.is_dir():
        return adrs
    for path in sorted(folder.glob("*.md")):
        if path.name.startswith(SKIP_PREFIXES):
            continue
        fields = parse_frontmatter(path)
        validate_adr(path, fields)
        adrs.append(Item(path=path, fields=fields))

    numbers: dict[int, str] = {}
    positions: dict[str, str] = {}
    for adr in adrs:
        number = adr.fields["adr"]
        if number in numbers:
            raise ItemError(f"{adr.path.name}: adr {number} is already {numbers[number]}")
        numbers[number] = adr.path.name
        if adr.status == "settled":
            position = str(adr.fields["position"])
            if position in positions:
                raise ItemError(
                    f"{adr.path.name}: position {position} is already {positions[position]}"
                )
            positions[position] = adr.path.name
            group = _position_key(adr)[0]
            if group not in groups:
                raise ItemError(
                    f"{adr.path.name}: group {group:02d} is not in _GROUPS.md — name the "
                    f"shelf before putting something on it"
                )
        else:
            successor = str(adr.fields["superseded_by"])
            if not (folder / f"{successor}.md").is_file():
                raise ItemError(f"{adr.path.name}: superseded_by {successor!r} does not exist")
    return adrs


def adr_summary(path: Path) -> str:
    """The body's first paragraph — the decision itself, which is the index line."""
    lines = path.read_text(encoding="utf-8").splitlines()
    end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    paragraph: list[str] = []
    for line in lines[end + 1 :]:
        if line.strip():
            paragraph.append(line.strip())
        elif paragraph:
            break
    summary = " ".join(paragraph)
    if not summary:
        raise ItemError(f"{path.name}: no body; the first paragraph is the index line")
    if len(summary) > ADR_SUMMARY_LIMIT:
        raise ItemError(
            f"{path.name}: first paragraph is {len(summary)} chars; the index line "
            f"holds {ADR_SUMMARY_LIMIT} — the decision goes first, the rationale after"
        )
    return summary


def render_architecture(adrs: list[Item], groups: dict[int, str]) -> str:
    lines = [
        NOTICE,
        "",
        "# ARCHITECTURE — what is settled",
        "",
        "Derived: each line is its ADR's first paragraph, so the file is the",
        "home and this index cannot drift from it. Order and grouping come from",
        "`position`, which is placement only; a superseded ADR keeps its number",
        "and its file in `docs/adr/` but leaves this index.",
        "",
    ]
    settled = [adr for adr in adrs if adr.status == "settled"]
    if not settled:
        lines.append("*No decisions yet. Copy `adr/_TEMPLATE.md` to `adr/<slug>.md`.*")
    for number in sorted(groups):
        members = sorted(
            (adr for adr in settled if _position_key(adr)[0] == number), key=_position_key
        )
        if not members:
            continue
        lines += [f"## {number:02d} — {groups[number]}", ""]
        for adr in members:
            indent = "  " * (len(_position_key(adr)) - 2)
            title = _cell(adr.fields.get("title"))
            lines.append(f"{indent}- [{title}](adr/{adr.path.name}) — {adr_summary(adr.path)}")
        lines.append("")
    lines.append(f"*{len(settled)} settled, {len(adrs) - len(settled)} superseded.*")
    return "\n".join(lines) + "\n"


def module_annotation(path: Path, source: str) -> str:
    """The docstring's first line, held to the rules that make it an annotation.

    Refusals happen at the gate rather than in review because the moment to
    name what a module owns is the moment it is created — a module that cannot
    say it in one line is usually a module that owns more than one thing.
    """
    try:
        docstring = ast.get_docstring(ast.parse(source))
    except SyntaxError as error:
        raise ItemError(f"{path.name}: does not parse — {error}") from error
    if not docstring or not docstring.strip():
        raise ItemError(f"{path.name}: no docstring; the first line is the scaffold annotation")
    first = docstring.strip().splitlines()[0].strip()
    if len(first) > ANNOTATION_LIMIT:
        raise ItemError(
            f"{path.name}: docstring first line is {len(first)} chars; "
            f"the scaffold column holds {ANNOTATION_LIMIT}"
        )
    lowered = first.lower()
    for word in BANNED_IN_ANNOTATION:
        if word in lowered:
            raise ItemError(
                f"{path.name}: docstring first line says {word!r} — name what the "
                f"module owns instead"
            )
    return first


def _scaffold_order(relative: str) -> tuple[int, str]:
    """Sort key: `src/sieve/` packages by layer, everything else by name."""
    parts = relative.split("/")
    if parts[:2] == ["src", "sieve"] and len(parts) > 3:
        package = parts[2]
        if package not in LAYER_ORDER:
            raise ItemError(
                f"src/sieve/{package}/ is not in LAYER_ORDER — a new package "
                f"states its place in the stack before it gets modules"
            )
        return (1 + LAYER_ORDER.index(package), relative)
    return (0, relative)


def collect_modules(repo: Path = REPO) -> list[tuple[str, str]]:
    """`(repo-relative path, annotation)` for every module under `SCAN_ROOTS`."""
    modules: list[tuple[str, str]] = []
    for root in SCAN_ROOTS:
        folder = repo / root
        if not folder.is_dir():
            continue
        relatives = sorted(
            (path.relative_to(repo).as_posix() for path in folder.rglob("*.py")),
            key=_scaffold_order,
        )
        for relative in relatives:
            path = repo / relative
            annotation = module_annotation(path, path.read_text(encoding="utf-8"))
            modules.append((relative, annotation))
    return modules


def forbidden_present(repo: Path = REPO) -> list[str]:
    return [entry for entry in FORBIDDEN if (repo / entry).exists()]


#: Vocabulary an ADR renamed away, still readable in old repos but dead here:
#: (the dead word as a regex, what excuses a line that says it, the verdict).
#: A line naming v1/v2 is quoting history; "not filters" is the rename naming
#: itself. Grows a row per buried word.
DEAD_LANGUAGE = [
    (r"filters?", r"\bv[12]\b|not filters", "adr/tools-not-filters.md"),
]

_CODE_SPAN = re.compile(r"`[^`]*`")


def dead_language(repo: Path = REPO) -> list[str]:
    """Lines in the binding docs still speaking a vocabulary an ADR buried.

    Scope is the prose that binds: `docs/*.md`, the ADRs, the items. Findings
    are exempt — a measurement record speaks the language of the repo it
    measured — and identifiers in `src/` are the Phase-1 spelling gate's job.
    A word fused into an identifier or path (`filter_base.py`,
    `tools-not-filters`) is a name, not language, and passes.
    """
    docs = repo / "docs"
    targets = [
        *sorted(docs.glob("*.md")),
        *sorted((docs / "adr").glob("*.md")),
        *sorted((docs / "todo").glob("*.md")),
    ]
    hits = []
    for path in targets:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            bare = _CODE_SPAN.sub("", line)
            for word, excuse, verdict in DEAD_LANGUAGE:
                if re.search(excuse, bare, re.IGNORECASE):
                    continue
                match = re.search(rf"(?<![\w/.-]){word}(?![\w/-])", bare, re.IGNORECASE)
                if match:
                    relative = path.relative_to(repo).as_posix()
                    hits.append(f"{relative}:{lineno}: '{match.group(0)}' is dead ({verdict})")
    return hits


def core_strays(repo: Path = REPO) -> list[str]:
    """Direct children of `core/` that ADR-6's enumeration does not admit."""
    folder = repo / "src" / "sieve" / "core"
    if not folder.is_dir():
        return []
    return sorted(
        path.name
        for path in folder.iterdir()
        if path.name not in CORE_CHILDREN and path.name != "__pycache__"
    )


def _spoken(text: str) -> str:
    """A phrase reduced to what two sentences have to share to say the same thing."""
    return " ".join(text.replace("`", "").lower().split())


def annotation_gaps(repo: Path = REPO) -> list[str]:
    """Ownership the component table assigns and the package's own line omits.

    The link SCAFFOLD's derivation does not weld. Deriving the annotation from
    the docstring makes it impossible for the tree to disagree with the
    docstring; the docstring is still a person typing a sentence the day the
    directory appears, and the decisions enumerating what the package owns land
    after — which is exactly when nothing rereads the line
    (`findings/2026.08.06-derived-docs-prove-the-copy-not-the-decision.md`).

    Containment, one direction, and only over the marked phrases. The line may
    say more than the row and may say it in its own words; what it may not do
    is leave one of them out. The weaker check available here — every package
    named in the table has a directory and vice versa — would have passed the
    three misses that prompted this.

    A missing table is a problem rather than a pass: a gate whose input can be
    deleted into silence is worse than none, because the next reader believes
    the lines were checked.
    """
    vision = repo / "docs" / "VISION.md"
    if not vision.is_file():
        return []
    text = vision.read_text(encoding="utf-8")
    if COMPONENT_HEADING not in text:
        return [f"docs/VISION.md has no component table under {COMPONENT_HEADING!r}"]
    section = text.split(COMPONENT_HEADING, 1)[1].split("\n## ", 1)[0]

    problems: list[str] = []
    rows = 0
    for line in section.splitlines():
        row = COMPONENT_ROW.match(line)
        if not row:
            continue
        rows += 1
        package = row["package"]
        phrases = [_spoken(phrase) for phrase in OWNED.findall(row["owns"])]
        if not phrases:
            problems.append(f"`{package}`'s row marks nothing it owns — the enumeration is bold")
            continue
        init = repo / "src" / "sieve" / package / "__init__.py"
        if not init.is_file():
            problems.append(f"`{package}` has a row and no src/sieve/{package}/__init__.py")
            continue
        try:
            line_ = _spoken(module_annotation(init, init.read_text(encoding="utf-8")))
        except ItemError as error:
            problems.append(str(error))
            continue
        missing = [phrase for phrase in phrases if phrase not in line_]
        if missing:
            problems.append(
                f"src/sieve/{package}/__init__.py does not name "
                + ", ".join(repr(phrase) for phrase in missing)
            )
    if not rows:
        problems.append("docs/VISION.md's component table has no rows the gate can read")
    return problems


def render_scaffold(modules: list[tuple[str, str]]) -> str:
    lines = [
        NOTICE,
        "",
        "# SCAFFOLD — where things live",
        "",
        "Derived: each annotation is its module docstring's first line, so the",
        "docstring is the home and this file cannot drift from it. Add a module",
        "with a one-line statement of what it owns and this file follows. The",
        "tree reads top of the stack first: a package may reach only what is",
        "listed below it.",
        "",
    ]
    if modules:
        width = max(len(path) for path, _ in modules)
        lines += ["```tree"]
        lines += [f"{path.ljust(width)}  # {annotation}" for path, annotation in modules]
        lines += ["```"]
    else:
        lines.append("*No modules yet.*")
    lines += [
        "",
        "## Absent by decision",
        "",
        "PLAN.md dropped these; the gate fails if one appears. A path leaves",
        "this list by a plan change, not by being built.",
        "",
        "```tree",
        *FORBIDDEN,
        "```",
    ]
    return "\n".join(lines) + "\n"


def queue_key(item: Item) -> tuple[int, int, tuple[int, ...], str]:
    """The whole priority order, as one sort key.

    Phase, then a step before a pool item, then the number or the priority,
    then the name. Three comparisons and no state: what runs next is a fact
    about the folder, so a queue reading it never has to know what ran before.

    **Phase outranks everything, including urgency.** An earlier phase is
    groundwork the later ones stand on, so a `low` in phase 0 precedes a `high`
    in phase 5 — the number already carries the claim that one must hold before
    the other is worth doing, and a priority that could jump it would be a
    second ordering laid over the first.

    **A step outranks a pool item in its own phase.** A step is what the phase
    committed to; a pool item is what got noticed while doing it.

    A step and a pool item never reach the third position together, so the two
    shapes it can hold — a dotted step and a bare priority rank — are never
    compared with each other.

    What this replaced: a boundary rule where a phase's pool was paid only when
    the next phase opened, plus an exemption for a phase already under way. Two
    pieces of state, and between them a pool nothing could reach — forty-nine
    owed items against a plan in its sixth phase, and a `priority` that ordered
    a drain that had never once run.
    """
    pooled = item.step_key is None
    return (
        UNPHASED if item.phase is None else item.phase,
        int(pooled),
        item.step_key or (item.priority_rank,),
        item.path.name,
    )


def queue(items: list[Item]) -> list[Item]:
    """Every open item, in the order the loop takes them.

    `awaiting-review` is absent by construction rather than by a filter that
    reads as an oversight: its next session is a review, and `next_action`
    reaches those first.
    """
    return sorted((i for i in items if i.status == "open"), key=queue_key)


def unspecified(items: list[Item]) -> list[str]:
    """Those that cannot be worked as written, for want of a criterion."""
    return [i.path.name for i in items if not str(i.fields.get("done_when", "")).strip()]


def next_takeable(items: list[Item]) -> Item | None:
    """The first open item in the order, whether or not it can be worked yet.

    Not filtered by `done_when`. Serving the first *specified* item instead
    would step over exactly the items that need specifying, which makes the
    queue drainable by ignoring them; and under a strict order it would let a
    `low` in a later phase outrank a `high` in an earlier one purely by having
    a criterion, which is a second ordering nobody wrote down.
    """
    return next(iter(queue(items)), None)


def next_action(items: list[Item]) -> tuple[str, Item | None]:
    """What the loop does next, as a role and the item it acts on.

    The role is the half `--next` used to leave to convention. A path alone can
    only start a work run, so an item at `awaiting-review` was indistinguishable
    from one that did not exist
    (`findings/loop/2026.08.07-awaiting-review-leaves-the-selection-rule-and-never-returns.md`).
    Naming the role is also what keeps a worker off its own verdict: the queue
    starts the session the role belongs to, so no one session is ever offered
    both.

    A pending review comes first — the item is finished and unadjudicated, and
    everything behind it is ordered on a status only the review can set. Then
    the head of the queue, as `work` when it carries a criterion and `specify`
    when it does not: an item with no `done_when` is not skipped and does not
    shut anything, it is simply the same item handed to the one role permitted
    to write one. `drained` is the only answer that means stop.
    """
    pending = sorted((i for i in items if i.status == "awaiting-review"), key=queue_key)
    if pending:
        return ("review", pending[0])
    item = next_takeable(items)
    if item is None:
        return ("drained", None)
    return (("work" if str(item.fields.get("done_when", "")).strip() else "specify"), item)


def gates(repo: Path = REPO) -> list[str]:
    """Refusals about the tree rather than about any one derived file.

    Every one runs and every one is reported, for the same reason the targets
    render independently: the session that has to fix these should see all of
    them from one run rather than one per run. None of them stops a target
    being written — a tree with a problem in it is exactly the tree whose
    indexes most need to be current, because the item recording the problem
    goes in one of them.
    """
    problems: list[str] = []
    lost = tracked_drift(repo / "docs" / "todo", repo)
    if lost:
        problems.append("items have been overwritten or removed: " + "; ".join(lost))
    built = forbidden_present(repo)
    if built:
        problems.append(f"absent-by-decision paths exist: {', '.join(built)}")
    strays = core_strays(repo)
    if strays:
        problems.append(
            f"core has children ADR-6 does not admit: {', '.join(strays)} — "
            f"revise adr/core-membership-is-closed.md first"
        )
    dead = dead_language(repo)
    if dead:
        problems.append("dead language: " + "; ".join(dead))
    gaps = annotation_gaps(repo)
    if gaps:
        problems.append("the component table and a package's own line disagree: " + "; ".join(gaps))
    return problems


def _architecture(adr_dir: Path) -> str:
    groups = parse_groups(adr_dir / "_GROUPS.md")
    return render_architecture(collect_adrs(adr_dir, groups), groups)


def derived(items: list[Item], repo: Path = REPO) -> list[tuple[Path, Callable[[], str]]]:
    """The four generated files, each with the thunk that renders it.

    A thunk rather than the text, because rendering is where the failures are
    and one target's failure must not be the other three's: the derived docs
    have four independent sources and share only this list.
    """
    docs = repo / "docs"
    findings, adr_dir = docs / "findings", docs / "adr"
    return [
        (docs / "todo" / INDEX_NAME, lambda: render(items, phase_titles(docs / "PLAN.md"))),
        (
            findings / INDEX_NAME,
            lambda: render_findings(
                collect_findings(findings), collect_findings(findings / "loop")
            ),
        ),
        (docs / "SCAFFOLD.md", lambda: render_scaffold(collect_modules(repo))),
        (docs / "ARCHITECTURE.md", lambda: _architecture(adr_dir)),
    ]


def main(argv: list[str] | None = None, repo: Path = REPO) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if the index is stale")
    parser.add_argument("--next", action="store_true", help="print the next takeable item's path")
    parser.add_argument("--mint", metavar="SLUG", help="start a new item, refusing a taken slug")
    args = parser.parse_args(argv)
    todo_dir = repo / "docs" / "todo"

    # Before `collect`, deliberately: a folder holding one item that will not
    # parse must still be able to accept a new one, or the way to record a
    # problem is shut by the problem.
    if args.mint:
        try:
            print(f"doc_index: minted {mint(args.mint, todo_dir).relative_to(repo).as_posix()}")
        except ItemError as error:
            print(f"doc_index: {error}", file=sys.stderr)
            return 1
        return 0

    try:
        items = collect(todo_dir)
    except ItemError as error:
        print(f"doc_index: {error}", file=sys.stderr)
        return 1

    # Answered here, ahead of every gate and every render: selection reads the
    # items and nothing else, and when it sat behind the four targets a single
    # over-limit docstring stopped the loop choosing at all — which is the one
    # state where an item cannot be taken to record the blocker.
    if args.next:
        role, item = next_action(items)
        # A `specify` run sees one item and would otherwise have no way to tell
        # a last straggler from a queue with fifty of these in front of it.
        if role == "specify":
            behind = len(unspecified(queue(items)))
            print(f"doc_index: {behind} open items have no `done_when`", file=sys.stderr)
        # stdout is the role and the path, in that order, one line: the queue
        # reads the role to pick which prompt starts and never has to infer it.
        print(f"{role} {item.path.relative_to(repo).as_posix()}" if item else role)
        return 0

    problems = gates(repo)
    for index, build in derived(items, repo):
        relative = index.relative_to(repo)
        try:
            content = build()
        except ItemError as error:
            # Named by target rather than by cause alone: what the reader needs
            # first is which of the four is now stale, and the module the
            # message goes on to name is one input to one of them.
            problems.append(f"{relative}: {error}")
            continue
        current = index.read_text(encoding="utf-8") if index.exists() else None
        if current == content:
            continue
        if args.check:
            problems.append(f"{relative} is stale — rerun the tool")
        else:
            index.write_text(content, encoding="utf-8")
            print(f"doc_index: wrote {relative}")
    for problem in problems:
        print(f"doc_index: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
