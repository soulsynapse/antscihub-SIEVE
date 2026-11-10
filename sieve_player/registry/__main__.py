"""`python -m sieve_player.registry [root ...]` reports; `--check` holds the package to its README
and fails on a type nothing produces or nothing expects."""
import os
import re
import sys

from . import FACETS, MARKER, __all__, discover, hint, is_tool, types

VIDEO = ("video", "bgr", "path")   # the one node that is not a tool: what it produces and expects

HERE = os.path.dirname(os.path.abspath(__file__))


def orphans(roots):
    """[(type, producers, expecters)] with an empty side, over the tools under `roots` and the video node."""
    return [(t, *pe) for t, pe in sorted(types(discover(*roots), [VIDEO]).items()) if not all(pe)]


def report(roots):
    for t, (p, ex) in sorted(types(discover(*roots), [VIDEO]).items()):
        print(f"{t:<8} from {', '.join(sorted(p)) or 'nothing'}  to {', '.join(sorted(ex)) or 'nothing'}")
    for e in discover(*roots):
        print(f"{e.name}  ({e.path})")
        if not e.ok:
            print(f"    could not import: {e.error}")
            continue
        for f in FACETS:
            v = e.get(f)
            if v is None:
                print(f"    {f:<16} unsaid   -> {hint(f)}")
            elif callable(v):
                print(f"    {f:<16} defined")
            else:
                print(f"    {f:<16} {v!r}")
    for root in roots:
        pkg = os.path.basename(os.path.abspath(root))
        others = []
        for fn in sorted(os.listdir(root)):
            stem, ext = os.path.splitext(fn)
            if ext == ".py" and not stem.startswith("_"):
                mod = sys.modules.get(f"{pkg}.{stem}")
                if mod is not None and not is_tool(mod):
                    others.append(fn)
        if others:
            print(f"not tools under {root} (no {hint(MARKER)!r}): {', '.join(others)}")


def check():
    """README's Exports == __all__; every facet is read by some sieve_player module outside here."""
    failures = []
    with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    section = readme.split("## Exports", 1)[1].split("\n## ", 1)[0]
    named = re.findall(r"^- `([A-Za-z_]\w*)", section, re.M)
    if sorted(named) != sorted(__all__):
        failures.append(f"README names {sorted(named)} but __all__ is {sorted(__all__)}")
    pkg = os.path.dirname(HERE)
    sources = ""
    for fn in os.listdir(pkg):
        if fn.endswith(".py"):
            with open(os.path.join(pkg, fn), encoding="utf-8") as f:
                sources += f.read()
    for facet in FACETS:
        if facet == MARKER:
            continue  # read here, by discovery; nothing else needs to
        if not re.search(rf"""[.\"']{facet}\b""", sources):
            failures.append(f"facet {facet!r} is probed but nothing in sieve_player reads it")
    for t, p, ex in orphans(["tools"]):
        failures.append(f"type {t!r} is {'produced' if p else 'expected'} by {', '.join(sorted(p or ex))} and {'expected' if p else 'produced'} by nothing")
    for msg in failures:
        print("FAIL", msg)
    print("registry check:", "ok" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--check"]:
        sys.exit(check())
    report(args or ["tools"])
