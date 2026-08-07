"""The derived docs: indexes, ARCHITECTURE, the scaffold, and `--next`.

Work items: one file each, YAML frontmatter, two shapes. A *sequenced* item
carries `step:` — dotted numbers whose first component is the phase, so
"02.3.1" is an aside inserted between "02.3" and "02.4" without renumbering
anything. A *pool* item carries `priority:` instead — noticed work that can
wait, attached to a phase or to none, and the priority is when it stops
waiting rather than a label (`next_takeable` has the rule). Between them the
number and the priority are the ordering, which is what lets `--next` be the
whole selection rule: the queue that runs the work never has to encode an
order, the repo holds it.

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
scaffold exists to catch.

Everything generated here is derived, never edited, and
`tests/docs/test_doc_index.py` fails when any of it drifts from the files it
describes — v2's discipline, cut to the subset v3 uses (no primer, no settled
table, no `after:` graph; the step numbers are the ordering those existed to
compute).

    uv run python scripts/doc_index.py           # rewrite everything generated
    uv run python scripts/doc_index.py --check   # exit 1 if anything is stale
    uv run python scripts/doc_index.py --next    # path of the next takeable item
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
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

#: The literal for "not gated". Spelled out and required so an ungated item is
#: a decision somebody made, not a field somebody skipped.
UNGATED = "nothing"


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
        raise ItemError(f"{path.name}: frontmatter is not valid YAML — {error}") from error
    if not isinstance(loaded, dict):
        raise ItemError(f"{path.name}: frontmatter must be a mapping")
    return {str(key): value for key, value in loaded.items()}


def validate(path: Path, fields: dict[str, Any]) -> None:
    for key in ("title", "status", "opened", "gated_on"):
        if not str(fields.get(key, "")).strip():
            raise ItemError(f"{path.name}: missing `{key}`")
    if fields["status"] not in STATUSES:
        raise ItemError(f"{path.name}: status {fields['status']!r} is not one of {STATUSES}")
    if fields["status"] == "deferred" and str(fields["gated_on"]).strip() == UNGATED:
        raise ItemError(f"{path.name}: deferred with `gated_on: {UNGATED}` is not a deferral")

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


def collect(todo_dir: Path = TODO_DIR) -> list[Item]:
    items: list[Item] = []
    for path in sorted(todo_dir.glob("*.md")):
        if path.name.startswith(SKIP_PREFIXES):
            continue
        fields = parse_frontmatter(path)
        validate(path, fields)
        items.append(Item(path=path, fields=fields))
    return items


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
        "One file per item; phases are `PLAN.md`'s. A sequenced item's `step` is",
        "its order — asides inserted with a decimal keep their place. A pool",
        "item's `priority` is its schedule: `--next` answers with an open",
        "`high` first, then a `normal` left behind by an earlier phase when the",
        "next step would open a new one, then the lowest open step. `low` is",
        "adopted or it expires. A pool item is reachable only once it carries a",
        "`done_when`. A worker moves an item to `awaiting-review`, a review to",
        "`done`.",
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

    open_count = sum(1 for item in items if item.status == "open")
    lines.append(f"*{len(items)} items, {open_count} open.*")
    return "\n".join(lines) + "\n"


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


def _pool_order(item: Item) -> tuple[int, int, str]:
    #: Unattached last: a pool item with no phase is repo-wide, so it has no
    #: place among the phases and only a name to order it by.
    return (1, 0, item.path.name) if item.phase is None else (0, item.phase, item.path.name)


def phase_started(items: list[Item], phase: int | None) -> bool:
    """A phase is under way once one of its steps has left `open`."""
    return any(i.phase == phase and i.step_key is not None and i.status != "open" for i in items)


def unreachable_highs(items: list[Item]) -> list[str]:
    """The open `high` pool items `next_takeable` must skip for want of a
    criterion, named so the skip is visible where it happens."""
    return [
        i.path.name
        for i in sorted(
            (
                i
                for i in items
                if i.status == "open"
                and i.step_key is None
                and i.fields.get("priority") == "high"
                and not str(i.fields.get("done_when", "")).strip()
            ),
            key=_pool_order,
        )
    ]


def next_takeable(items: list[Item]) -> Item | None:
    """The next item, in three tiers. `awaiting-review` is not takeable in any
    of them — its next session is a review, and the review queue entry names
    itself.

    A pool item's `priority` is its schedule, which is the whole reason the
    pool is reachable at all: selecting only on `step` made a priority a label
    nothing read, and forty-five asides accumulated against five closed. So
    `high` — a defect in code that already landed — preempts the next planned
    step wherever it sits, on the argument that the review which found it had
    the subject loaded and no later session will. `normal` is paid at a phase
    boundary, where the evidence is still fresh and the schedule has a seam:
    only a phase that has not begun is held up, and only by phases before it,
    so a normal minted against work the phase has not done yet never blocks
    the step that would do it. `low` is never takeable on its own — it is
    adopted by an item that touches the same file, or it expires.

    Takeability requires `done_when` either way. A pool item without one is
    skipped rather than served, because a session handed an item with no
    criterion writes its own, which is the one thing the open ->
    awaiting-review -> done protocol exists to make impossible."""
    open_items = [i for i in items if i.status == "open"]
    step = min(
        (i for i in open_items if i.step_key is not None),
        key=lambda i: i.step_key or (),
        default=None,
    )
    pool = [
        i for i in open_items if i.step_key is None and str(i.fields.get("done_when", "")).strip()
    ]

    high = sorted((i for i in pool if i.fields.get("priority") == "high"), key=_pool_order)
    if high:
        return high[0]
    if step is None:
        return None
    if not phase_started(items, step.phase):
        stranded = sorted(
            (
                i
                for i in pool
                if i.fields.get("priority") == "normal"
                and (i.phase is None or i.phase < (step.phase or 0))
            ),
            key=_pool_order,
        )
        if stranded:
            return stranded[0]
    return step


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if the index is stale")
    parser.add_argument("--next", action="store_true", help="print the next takeable item's path")
    args = parser.parse_args(argv)

    try:
        items = collect()
        built = forbidden_present()
        if built:
            raise ItemError(f"absent-by-decision paths exist: {', '.join(built)}")
        strays = core_strays()
        if strays:
            raise ItemError(
                f"core has children ADR-6 does not admit: {', '.join(strays)} — "
                f"revise adr/core-membership-is-closed.md first"
            )
        dead = dead_language()
        if dead:
            raise ItemError("dead language: " + "; ".join(dead))
        targets = [
            (TODO_DIR / INDEX_NAME, render(items, phase_titles())),
            (
                FINDINGS_DIR / INDEX_NAME,
                render_findings(collect_findings(FINDINGS_DIR), collect_findings(LOOP_DIR)),
            ),
            (SCAFFOLD, render_scaffold(collect_modules())),
        ]
        groups = parse_groups()
        targets.append((ARCHITECTURE, render_architecture(collect_adrs(ADR_DIR, groups), groups)))
    except ItemError as error:
        print(f"doc_index: {error}", file=sys.stderr)
        return 1

    if args.next:
        # A high the selector had to skip is the failure this rule was written
        # to end, so it is named on stderr rather than left to be inferred from
        # a queue that quietly moved on. stdout stays the path alone: the queue
        # reads it.
        for name in unreachable_highs(items):
            print(f"doc_index: {name} is high and has no `done_when`", file=sys.stderr)
        item = next_takeable(items)
        print(item.path.relative_to(REPO).as_posix() if item else "nothing takeable")
        return 0

    stale = False
    for index, content in targets:
        current = index.read_text(encoding="utf-8") if index.exists() else None
        if current == content:
            continue
        if args.check:
            stale = True
            print(
                f"doc_index: {index.relative_to(REPO)} is stale — rerun the tool", file=sys.stderr
            )
        else:
            index.write_text(content, encoding="utf-8")
            print(f"doc_index: wrote {index.relative_to(REPO)}")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
