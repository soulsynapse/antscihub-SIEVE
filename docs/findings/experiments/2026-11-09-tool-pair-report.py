"""Every pair of tools that look like one tool declared twice, from the registry and the source alone:
a shared operation word once kind words are stripped, or the same set of top-level names. A
difflib ratio over the source was tried and dropped: forty short modules share settings and
__main__ boilerplate, so it rated fifty pairs alike and the two real ones lowest. A report to read, not a test; a pair it
names is a question. Run from the repo root."""
import ast
import itertools
import sys

sys.path.insert(0, ".")
from sieve_player.registry import FACETS, discover  # noqa: E402

KIND_WORDS = {"bgr", "gray", "hsv", "mask", "flow", "blobs", "tracks", "signal", "path", "plane", "table"}


def verb(name):
    return "-".join(w for w in name.split("-") if w not in KIND_WORDS) or name


def top_names(tree):
    out = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            out |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return out - set(FACETS) - {"SIEVE_TOOL"}


def body_text(src):
    lines = [l for l in src.splitlines() if not l.startswith(("NAME", "KIND", "EXPECTS", "PRODUCES", "SIEVE_TOOL", "import", "from"))]
    return "\n".join(lines)


def main():
    tools = []
    for e in discover("tools"):
        if not e.ok:
            continue
        src = open(e.path, encoding="utf-8").read()
        tree = ast.parse(src)
        doc = ast.get_docstring(tree) or ""
        body = body_text(src.replace(doc, ""))
        tools.append((e.name, top_names(tree), body, e.get("EXPECTS"), e.get("PRODUCES")))
    print("| a | b | shared verb | names shared / union | a expects -> produces | b expects -> produces |")
    print("|---|---|---|---|---|---|")
    for (a, na, ba, ea, pa), (b, nb, bb, eb, pb) in itertools.combinations(tools, 2):
        shared = verb(a) == verb(b)
        inter, union = len(na & nb), len(na | nb) or 1
        if shared or (inter / union >= 0.6 and inter >= 3):
            print(f"| {a} | {b} | {'yes' if shared else ''} | {inter}/{union} | {ea} -> {pa} | {eb} -> {pb} |")


if __name__ == "__main__":
    main()
