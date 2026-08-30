"""Vocab convention check: the shape of an entry, and whether its citations
still resolve.

Two failures, both seen. An entry grows until nobody reads it. And an entry
cites a symbol that later moves — `serve.Ordinals` went to `sieve/ordinals.py`
and left the paragraph *defining* position reading false — so the fix is not to
stop citing code but to keep the citations under one heading and check that
heading. The definition must hold across a refactor; `## Where it lives` is
expected to move.

Bare backticked names (`ROLES`, `bind`) are deliberately not resolved: telling
a symbol from prose needs a guess, and a check with false positives is a check
somebody turns off.

Run: `uv run python -m checks.vocab`
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

VOCAB = "docs/vocab"
GLOSS_WORDS = 40
DEFINITION_WORDS = 150
#: The whole entry. An unsettled one is allowed more because it is a different
#: genre — an argument enumerating live senses, where the citations are the
#: content — but it is capped too, or it grows into the essay this prevents.
ENTRY_WORDS = 320
UNSETTLED_WORDS = 400

#: Trees whose modules a dotted citation may name.
SOURCES = ("src", "tools", "experiments", "checks", "scripts", "mockup")

REQUIRED = {"title", "group", "position", "gloss", "origin"}
OPTIONAL = {"defined", "raised", "status"}
ORIGINS = {"emergent", "decided"}

SETTLED_SECTIONS = ("Where it lives",)
UNSETTLED_SECTIONS = ("Senses", "Fork")

CODE = re.compile(r"`([^`]+)`")
SECTION = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
DOTTED = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$")


def front_matter(text: str) -> tuple[dict[str, str], str]:
    """A note's `key: value` header and the body under it, hand-parsed.

    The same shape `scripts/doc_index.py` reads, and for the same reason: the
    header is flat scalars and the repo has no YAML dependency to add.
    """
    if not text.startswith("---\n"):
        return {}, text
    header, _, body = text[4:].partition("\n---\n")
    fields = {}
    for line in header.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip("\"'")
    return fields, body


class Tree:
    """Every name the source trees define, by module and by class.

    Collected from the AST rather than by import: this runs where the tools'
    solvers are not installed, which is the same reason `checks/adr0010.py` is
    static.
    """

    def __init__(self, root: Path) -> None:
        self.modules: dict[str, set[str]] = {}
        self.classes: dict[str, set[str]] = {}
        self.paths: set[str] = set()
        for source in SOURCES:
            for path in (root / source).rglob("*.py"):
                self.read(root, path)
        for path in root.rglob("*.md"):
            if not {".venv", ".git"} & set(path.parts):
                self.paths.add(path.relative_to(root).as_posix())

    def read(self, root: Path, path: Path) -> None:
        self.paths.add(path.relative_to(root).as_posix())
        try:
            tree = ast.parse(path.read_bytes().decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            return
        names = self.modules.setdefault(path.stem, set())
        stack = [(tree, None)]
        while stack:
            node, holder = stack.pop()
            for child in ast.iter_child_nodes(node):
                bound = set()
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef)):
                    bound.add(child.name)
                elif isinstance(child, (ast.Assign, ast.AnnAssign)):
                    targets = (child.targets if isinstance(child, ast.Assign)
                               else [child.target])
                    for target in targets:
                        if isinstance(target, ast.Name):
                            bound.add(target.id)
                        elif isinstance(target, ast.Attribute):
                            bound.add(target.attr)
                names |= bound
                if holder:
                    # A dataclass field is a name of its class as much as a
                    # method is: `Tool.role` is an annotation and nothing else.
                    self.classes.setdefault(holder, set()).update(bound)
                is_class = isinstance(child, ast.ClassDef)
                stack.append((child, child.name if is_class else holder))

    def has_path(self, ref: str) -> bool:
        """Whether some file in the tree ends with this path.

        Matched from the tail so an entry can write `contract/edges.py` and
        not the full path from the root, which is how the tree talks about
        itself. A move still fails: nothing ends with the old tail.
        """
        ref = ref.lstrip("/")
        if ref.endswith("/"):  # a directory, named as the tree names one
            return any(f"/{ref}" in f"/{path}" for path in self.paths)
        return any(path == ref or path.endswith(f"/{ref}")
                   for path in self.paths)

    def resolves(self, ref: str) -> bool | None:
        """Whether a dotted citation still names something, or None if the
        head is nothing this repo defines and so nothing this can judge."""
        head, _, tail = ref.rpartition(".")
        head = head.rpartition(".")[2]
        if head in self.modules:
            return tail in self.modules[head]
        if head in self.classes:
            return tail in self.classes[head]
        return None


def citations(text: str) -> list[str]:
    """Backticked spans that are unambiguously a path or a dotted name."""
    found = []
    for span in CODE.findall(text):
        ref = span.split("(")[0].strip().rstrip(".,;:")
        if any(c in ref for c in " \"'[]{}=<>-*") or not ref:
            continue
        if ref.endswith((".py", ".md")) or "/" in ref or DOTTED.match(ref):
            found.append(ref)
    return found


def check(path: Path, text: str, tree: Tree) -> list[str]:
    fields, body = front_matter(text)
    bad = []
    unsettled = fields.get("status") == "unsettled"

    missing = REQUIRED - set(fields)
    if missing:
        bad.append(f"frontmatter is missing {', '.join(sorted(missing))}")
    unknown = set(fields) - REQUIRED - OPTIONAL
    if unknown:
        bad.append(f"frontmatter has unknown {', '.join(sorted(unknown))}")
    if fields.get("origin") not in ORIGINS and "origin" in fields:
        bad.append("origin is emergent or decided, not "
                   f"{fields['origin']!r}")
    if unsettled and "raised" not in fields:
        bad.append("an unsettled term records `raised`")

    gloss = fields.get("gloss", "")
    if len(gloss.split()) > GLOSS_WORDS:
        bad.append(f"gloss is {len(gloss.split())} words, over {GLOSS_WORDS}"
                   " — it is what VOCAB.md prints, so it has to scan")
    if "`" in gloss:
        bad.append("gloss names code; the gloss outlives the code")

    cap = UNSETTLED_WORDS if unsettled else ENTRY_WORDS
    if len(body.split()) > cap:
        bad.append(f"the entry is {len(body.split())} words, over {cap} — say "
                   "where to look and what could not be derived by looking")

    definition = SECTION.split(body)[0]
    words = len(definition.split())
    if words > DEFINITION_WORDS:
        bad.append(f"the definition is {words} words, over {DEFINITION_WORDS}"
                   " — evidence belongs under a heading, not before one")
    for ref in citations(definition):
        bad.append(f"the definition cites `{ref}`; code citations belong "
                   "under `## Where it lives`, which is checked and expected "
                   "to move")

    headings = SECTION.findall(body)
    wanted = UNSETTLED_SECTIONS if unsettled else SETTLED_SECTIONS
    for section in wanted:
        if section not in headings:
            bad.append(f"no `## {section}` section")

    for ref in citations(body):
        if ref.endswith((".py", ".md")) or "/" in ref:
            if not tree.has_path(ref):
                bad.append(f"`{ref}` is not a file in the tree")
        elif tree.resolves(ref) is False:
            bad.append(f"`{ref}` no longer resolves; it moved or was renamed")

    for link in LINK.findall(body):
        if link.startswith(("http:", "https:", "#")):
            continue
        if not (path.parent / link.split("#")[0]).exists():
            bad.append(f"the link to {link} points at nothing")

    return bad


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    tree = Tree(root)
    failures = 0
    for path in sorted((root / VOCAB).glob("*.md")):
        if path.name.startswith("_"):
            continue
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
        for problem in check(path, text, tree):
            print(f"{VOCAB}/{path.name}: {problem}")
            failures += 1
    if failures:
        print(f"\n{failures} to fix; the convention is "
              f"{VOCAB}/_TEMPLATE.md")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
