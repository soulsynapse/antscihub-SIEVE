"""Which of each tool's DEFAULTS no computing facet reads.

    python -X utf8 docs/findings/experiments/2026-11-16-which-settings-no-run-reads.py tools

A setting counts as read where its name is a string literal in a computing facet of the tool, or in
any function of the module or of the folder's `_*.py` files that facet reaches by name. So a name
that is a literal there for another reason is counted as read, and a setting read only under some
value of another is counted as read. A tool whose DEFAULTS is no dict literal is named and skipped.
"""
import ast
import os
import sys

ROOT = sys.argv[1]
COMPUTE = ("run", "step", "fold", "cut_file", "cut_files", "select", "matches")
SHOW = ("draw", "pick", "settings")


def load(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read())


def named(tree):
    return {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


def literals_and_names(node):
    lits, names = set(), set()
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            lits.add(n.value)
        elif isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.Attribute):
            names.add(n.attr)
    return lits, names


shared = {}
for fn in sorted(os.listdir(ROOT)):
    if fn.startswith("_") and fn.endswith(".py") and fn != "__init__.py":
        shared.update(named(load(os.path.join(ROOT, fn))))


def reach(start, local):
    seen, lits, todo = set(), set(), list(start)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        node = local.get(name) or shared.get(name)
        if node is None:
            continue
        found, names = literals_and_names(node)
        lits |= found
        todo += [x for x in names if x in local or x in shared]
    return lits


def defaults(tree):
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DEFAULTS" for t in n.targets):
            if isinstance(n.value, ast.Dict):
                return [k.value for k in n.value.keys if isinstance(k, ast.Constant)]
            return None
    return []


total = unread_total = 0
for fn in sorted(os.listdir(ROOT)):
    if fn.startswith("_") or not fn.endswith(".py"):
        continue
    tree = load(os.path.join(ROOT, fn))
    local = named(tree)
    keys = defaults(tree)
    if keys is None:
        print(f"{fn}: DEFAULTS is no dict literal")
        continue
    computing = reach([f for f in COMPUTE if f in local], local)
    showing = reach([f for f in SHOW if f in local], local)
    unread = [k for k in keys if k not in computing]
    total += len(keys)
    unread_total += len(unread)
    if unread:
        print(f"{fn}: {len(keys)} settings, read by no computing facet: {unread}; "
              f"of them read by draw, pick or settings: {[k for k in unread if k in showing]}"
              f"{'; has key_params' if 'key_params' in local else ''}")
print(f"{total} settings, {unread_total} read by no computing facet")
