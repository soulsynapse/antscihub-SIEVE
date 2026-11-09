"""`python -m sieve_player document.json [root ...]`: open a saved document against the tools the
registry finds under the roots (default: tools/). With `--plan`, print the plan instead: each node,
its kind, its key, its role in the walk, whether the walk steps it, and its standing, and exit."""
import sys

from . import play
from .registry import discover


def show_plan(path, tools):
    from . import document
    from .plan import base_key, plan, walked

    doc = document.load(path, tools)
    p = plan(doc, tools, base_key(doc.video_path(), document.video_output(doc)))
    walk = walked(p.entries, p.chain, p.shown)
    width = max(len(n.id) for n in doc.nodes)
    for n in doc.nodes:
        e = p.entries[n.id]
        role = "walked" if n.id == walk else "head" if n.id in p.heads else "chain" if n.id in p.chain else ""
        steps = "" if n.id not in p.chain else "step" if e.steps else f"whole after {e.whole_by}" if e.whole_by else "whole"
        print(f"{n.id:<{width}}  {'?' if n.unresolved else e.kind:<8} {e.key}  {role:<6} {steps:<6} {e.standing}")
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    show = "--plan" in argv
    argv = [a for a in argv if a != "--plan"]
    doc, roots = argv[0], argv[1:] or ["tools"]
    if show:
        return show_plan(doc, {e.name: e.module for e in discover(*roots) if e.ok})
    return play(doc, tools=discover(*roots))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
