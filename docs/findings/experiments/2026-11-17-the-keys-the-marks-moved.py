"""before.md and marked.md, the baseline one-off's output without and with the marks: per part and
document, the nodes whose key differs."""
import re
import sys


def keys(path):
    out, part, doc = {}, 0, None
    for line in open(path, encoding="utf-8"):
        if line.startswith("## "):
            part += 1
        elif line.startswith("### "):
            doc = line[4:].strip().strip("`")
        elif (m := re.match(r"\| (\S+) \| ([0-9a-f]{16}) \|", line)) or (m := re.match(r"(\S+)\s+\w+\s+([0-9a-f]{16})\b", line)):
            out[(part, doc, m.group(1))] = m.group(2)
    return out


a, b = keys(sys.argv[1]), keys(sys.argv[2])
assert set(a) == set(b)
last = None
for (part, doc, node), key in a.items():
    if b[(part, doc, node)] != key:
        if (part, doc) != last:
            print(f"\n{'`--plan`' if part == 1 else 'in the player'}, `{doc}`\n")
            print("| node | key before | key now |\n| --- | --- | --- |")
            last = (part, doc)
        print(f"| {node} | {key} | {b[(part, doc, node)]} |")
print(f"\n{sum(a[k] != b[k] for k in a)} of {len(a)} keys differ")
