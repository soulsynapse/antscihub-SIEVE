"""Vocab convention check: an entry is its frontmatter, and nothing else.

A term gets a short definition and no argument. The gloss is the whole entry —
VOCAB.md quotes it verbatim, so the index is the vocabulary rather than a
summary of it — and a body is what an entry grows before it starts governing.

One sense per entry. A word the tree uses two ways gets two files, qualified
the way a dictionary qualifies a homonym: `node (contract)` and
`node (orchestrator)` are different words that are spelled alike, and listing
them apart says so without anybody having to settle it.

Nothing here resolves a symbol, because nothing here names one. Where a word
lives is what grep is for, and what a module's own docstring is for.

Run: `uv run python -m checks.vocab`
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VOCAB = "docs/vocab"
GLOSS_WORDS = 40

REQUIRED = {"title", "group", "position", "gloss", "origin", "defined"}
ORIGINS = {"emergent", "decided"}

#: A qualified homonym: the word, then the domain that tells it from its twin.
TITLE = re.compile(r"^[a-z][a-z ]*( \([a-z]+\))?$")


def front_matter(text: str) -> tuple[dict[str, str], str]:
    """A note's `key: value` header and whatever follows it.

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


def check(text: str) -> list[str]:
    fields, body = front_matter(text)
    bad = []

    missing = REQUIRED - set(fields)
    if missing:
        bad.append(f"frontmatter is missing {', '.join(sorted(missing))}")
    unknown = set(fields) - REQUIRED
    if unknown:
        bad.append(f"frontmatter has unknown {', '.join(sorted(unknown))}")
    if "origin" in fields and fields["origin"] not in ORIGINS:
        bad.append(f"origin is emergent or decided, not {fields['origin']!r}")
    if "title" in fields and not TITLE.match(fields["title"]):
        bad.append(f"{fields['title']!r} is a word, or a word and the domain "
                   "that tells it from its twin: `node (contract)`")

    gloss = fields.get("gloss", "")
    if len(gloss.split()) > GLOSS_WORDS:
        bad.append(f"gloss is {len(gloss.split())} words, over {GLOSS_WORDS}")
    if "`" in gloss:
        bad.append("gloss names code; a definition outlives the code")

    if body.strip():
        bad.append("an entry is its frontmatter. A second sense is a second "
                   "entry; where the word lives is what grep is for")

    return bad


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures = 0
    for path in sorted((root / VOCAB).glob("*.md")):
        if path.name.startswith("_"):
            continue
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
        for problem in check(text):
            print(f"{VOCAB}/{path.name}: {problem}")
            failures += 1
    if failures:
        print(f"\n{failures} to fix; the convention is {VOCAB}/_TEMPLATE.md")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
