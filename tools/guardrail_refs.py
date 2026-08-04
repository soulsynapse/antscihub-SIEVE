"""A claimed gate must name something that exists, and a fired trigger must have an item.

Two recurrences with a paid-for track record, both converted to test failures
here.

`AUTO-GUARDRAILS.md` once wrote "**Check:** <the test that should exist>" in
the same voice for checks that existed and checks that did not, so three
unbuilt checks read as done for two weeks. The file now says **OPEN** where
nothing is keeping a rule — but the other half of that failure is a check that
*did* exist and then got renamed, which reads as done forever. So every test a
guardrail claims is named as `path::name` and resolved by AST, and every
`.importlinter` contract it cites is resolved by parse.

`§2`'s **Trigger:** fired at schema v3 — `Edge.port`, `Project.detector`, the
pin fields — and nobody noticed, so the most valuable unwritten check in the
file stayed unwritten through the very item that should have created it. A
fired trigger is therefore a parse failure unless it names the `docs/todo/`
item it became.

**The grammar**, which is why AUTO-GUARDRAILS reads the way it does:

    **Trigger: NOT FIRED** (re-checked 2026.07.28[, prose]) — prose
    **Trigger: FIRED** (audited 2026.07.28) → docs/todo/<slug>.md — prose

The state lives *inside* the bold, so `**Trigger:**` with nothing after the
colon is the construct being named in prose rather than declared (the "Adding
one" section does exactly that) — and a declaration miswritten in that shape is
caught, because a bare `**Trigger:**` followed by FIRED is an error rather than
a skip. Text is flattened before matching: every one of these lines is wrapped
across two source lines, and a checker that reads lines cannot see them.

REWORK.md's **Gate:** lines are the same claim in the other direction — a rule
graduates when its gate names something that exists — and are checked against
the same two resolvers, with `OPEN` as the honest third answer. They are
paragraph-initial there, which is what separates a declaration from the
sentence in *How a rule leaves this file* that names the construct.

    uv run python tools/guardrail_refs.py            # report
    uv run python tools/guardrail_refs.py --check    # exit 1 on an unresolved claim
"""

from __future__ import annotations

import argparse
import ast
import configparser
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from doc_refs import REPO_ROOT, body_of

GUARDRAILS = REPO_ROOT / "docs" / "AUTO-GUARDRAILS.md"
ARCHITECTURE = REPO_ROOT / "docs" / "ARCHITECTURE.md"
REWORK = REPO_ROOT / "docs" / "REWORK.md"

#: Docs whose test claims are checked. Both assert that a named check keeps a
#: named rule; the rest of the tree points at test *files*, which
#: `doc_refs.py` already resolves.
TEST_CLAIM_DOCS = (GUARDRAILS, ARCHITECTURE)

TEST_REF = re.compile(r"`(tests/[^`\s]+\.py)::([A-Za-z_][A-Za-z0-9_]*)`")
BACKTICKED = re.compile(r"`([^`\n]+)`")
DATE = re.compile(r"\b\d{4}\.\d{2}\.\d{2}\b")

#: The state is inside the bold; an empty payload is the construct named in
#: prose. The tail is bounded so one malformed declaration cannot swallow the
#: next section's text and report a second, phantom failure.
TRIGGER = re.compile(r"\*\*Trigger:(?P<state>[^*]*)\*\*(?P<tail>.{0,320})")
DECLARED = re.compile(r"^\s*\((?P<paren>[^)]*)\)(?P<rest>.*)")
ITEM = re.compile(r"^\s*(?:→|->)\s*`?(?P<item>docs/todo/[a-z0-9-]+\.md)`?")


def flatten(path: Path) -> str:
    """The document below its frontmatter, as one line."""
    return " ".join(body_of(path).split())


def defined_names(module: Path) -> set[str]:
    """Every function and class name in a module, nested ones included.

    AST rather than `pytest --collect-only`: no subprocess, and it sees a test
    that was renamed but still collects — which is the failure this catches.
    Nested because half the checks a guardrail cites are methods on a class.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }


def named_checks(path: Path) -> list[tuple[str, str]]:
    """`(file, name)` for every ``path.py::name`` token in a document."""
    return [(str(file), str(name)) for file, name in TEST_REF.findall(flatten(path))]


def unresolved_tests(paths: Sequence[Path] = TEST_CLAIM_DOCS) -> list[tuple[str, str]]:
    """`(doc, token)` for every named check that no longer exists."""
    missing: list[tuple[str, str]] = []
    for path in paths:
        for file, name in named_checks(path):
            module = REPO_ROOT / file
            if not module.is_file() or name not in defined_names(module):
                missing.append((path.name, f"{file}::{name}"))
    return missing


def contract_names(root: Path = REPO_ROOT) -> set[str]:
    """Every contract id in `.importlinter`."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string((root / ".importlinter").read_text(encoding="utf-8"))
    prefix = "importlinter:contract:"
    return {name.removeprefix(prefix) for name in parser.sections() if name.startswith(prefix)}


#: A contract id is lowercase with at least one hyphen, and counts as a claim
#: only within this many characters of `.importlinter`. Both halves were
#: needed. Dropping the hyphen sweeps in `cv2`, `gui`, `checks` — every
#: backticked word near the citation. Widening the marker to the word
#: *contract* sweeps in item slugs, because REWORK.md's rules are *about*
#: contracts. The window reaches across the clause a contract is cited in and
#: stops short of a paragraph.
#:
#: The cost is `layers`, the one contract with no hyphen in its name: cited by
#: that name, it would be unresolvable here. The docs call it "the layer
#: contract" throughout, so nothing is currently missed — rename it and this
#: comment is the note that says why the check went quiet.
CITATION_WINDOW = 160
CONTRACT_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+")


def contract_claims(path: Path) -> list[str]:
    """Backticked tokens shaped like a contract id, in citation position."""
    text = flatten(path)
    claims: list[str] = []
    for match in BACKTICKED.finditer(text):
        token = str(match.group(1)).strip()
        if not CONTRACT_ID.fullmatch(token):
            continue
        window = text[max(0, match.start() - CITATION_WINDOW) : match.end() + CITATION_WINDOW]
        if ".importlinter" in window:
            claims.append(token)
    return claims


def unresolved_contracts(
    paths: Sequence[Path] = (GUARDRAILS, ARCHITECTURE, REWORK),
) -> list[tuple[str, str]]:
    known = contract_names()
    return [
        (path.name, token)
        for path in paths
        for token in contract_claims(path)
        if token not in known
    ]


@dataclass(frozen=True)
class Trigger:
    """One `**Trigger:**` declaration, parsed."""

    state: str
    date: str
    item: str | None

    @property
    def fired(self) -> bool:
        return self.state == "FIRED"


def triggers(path: Path = GUARDRAILS) -> tuple[list[Trigger], list[str]]:
    """`(parsed, complaints)` for every trigger declaration in a document."""
    parsed: list[Trigger] = []
    complaints: list[str] = []

    for match in TRIGGER.finditer(flatten(path)):
        state = " ".join(str(match.group("state")).split())
        tail = str(match.group("tail"))
        if not state:
            if re.match(r"\s*(NOT\s+)?FIRED", tail):
                complaints.append(f"state belongs inside the bold: **Trigger:**{tail[:40]}")
            continue  # the construct named in prose, not a declaration
        if state not in ("FIRED", "NOT FIRED"):
            complaints.append(f"unknown trigger state {state!r}")
            continue
        declared = DECLARED.match(tail)
        if declared is None or not DATE.search(str(declared.group("paren"))):
            complaints.append(f"{state} carries no (YYYY.MM.DD) date: {tail[:60]}")
            continue
        date = str(DATE.search(str(declared.group("paren"))).group(0))  # type: ignore[union-attr]
        item: str | None = None
        if state == "FIRED":
            named = ITEM.match(str(declared.group("rest")))
            if named is None:
                complaints.append(f"FIRED ({date}) names no item: {tail[:60]}")
                continue
            item = str(named.group("item"))
            if not (REPO_ROOT / item).is_file():
                complaints.append(f"FIRED ({date}) -> {item}, which does not exist")
                continue
        parsed.append(Trigger(state=state, date=date, item=item))

    return parsed, complaints


def gate_paragraphs(path: Path = REWORK) -> list[str]:
    """Every paragraph opening with `**Gate:**`, as one line each.

    Paragraph-initial is the discriminator: the sentence in *How a rule leaves
    this file* that names the construct is mid-paragraph, and a rule's own
    gate never is.
    """
    paragraphs: list[str] = []
    current: list[str] | None = None
    for line in body_of(path).splitlines():
        if line.startswith("**Gate:**"):
            current = [line]
        elif current is not None:
            if not line.strip():
                paragraphs.append(" ".join(" ".join(current).split()))
                current = None
            else:
                current.append(line)
    if current is not None:
        paragraphs.append(" ".join(" ".join(current).split()))
    return paragraphs


def ungated(path: Path = REWORK) -> list[str]:
    """Gate lines that name neither a live check nor OPEN.

    A gate may name a contract, a specific check, or a whole test module — all
    three are things that exist and can be looked at. `OPEN` is the honest
    third answer and is what keeps rule graduation visible rather than
    automated.
    """
    known = contract_names()
    bad: list[str] = []
    for paragraph in gate_paragraphs(path):
        if "OPEN" in paragraph:
            continue
        resolved = False
        for file, name in TEST_REF.findall(paragraph):
            module = REPO_ROOT / str(file)
            resolved |= module.is_file() and str(name) in defined_names(module)
        for token in BACKTICKED.findall(paragraph):
            token = str(token).strip()
            resolved |= token in known
            resolved |= token.startswith("tests/") and (REPO_ROOT / token).is_file()
        if not resolved:
            bad.append(paragraph[:100])
    return bad


def trigger_health(path: Path = GUARDRAILS) -> str:
    """One line: how many triggers are armed, how many fired, how stale.

    Dates are read from the file rather than compared against the clock —
    `docs/.state.md` is compared byte-for-byte by `--check`, so anything that
    moves on its own makes the gate fail on a day nobody edited anything.
    """
    parsed, _ = triggers(path)
    fired = [trigger for trigger in parsed if trigger.fired]
    armed = [trigger for trigger in parsed if not trigger.fired]
    oldest = min((trigger.date for trigger in armed), default=None)
    tail = f"oldest re-check {oldest}." if oldest else "none armed."
    return f"**Triggers:** {len(fired)} fired and carried into an item, {len(armed)} armed; {tail}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 on an unresolved claim")
    args = parser.parse_args(argv)

    tests = unresolved_tests()
    contracts = unresolved_contracts()
    parsed, complaints = triggers()
    bad_gates = ungated()

    print(f"guardrail_refs: {trigger_health()}")
    for doc, token in tests:
        print(f"  RENAMED  {doc} -> {token}")
    for doc, token in contracts:
        print(f"  NO SUCH CONTRACT  {doc} -> {token}")
    for complaint in complaints:
        print(f"  TRIGGER  {complaint}")
    for gate in bad_gates:
        print(f"  GATE     {gate}")
    for trigger in parsed:
        if trigger.fired:
            print(f"  fired {trigger.date} -> {trigger.item}")

    broken = bool(tests or contracts or complaints or bad_gates)
    return 1 if (args.check and broken) else 0


if __name__ == "__main__":
    raise SystemExit(main())
