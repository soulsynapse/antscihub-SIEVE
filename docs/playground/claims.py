"""Which claims of docs/playground/claims.md a change has put in doubt.

A claim line is `- [id] the claim | files: a.py, b.py | leans: what rests on it | checked: <commit>`.
A claim is in doubt when any of its files differs between the commit it was checked at and the
working tree. Run: python docs/playground/claims.py [id <commit>]; with an id and a commit it
stamps that claim as checked there.
"""
import re
import subprocess
import sys
from pathlib import Path

LEDGER = Path(__file__).with_name("claims.md")
LINE = re.compile(r"- \[(?P<id>\w+)\] (?P<claim>.*?) \| files: (?P<files>.*?) \| leans: (?P<leans>.*?) \| checked: (?P<at>\w+)\s*$")


def claims():
    return [m.groupdict() for line in LEDGER.read_text(encoding="utf-8").splitlines() if (m := LINE.match(line))]


def touched(at, files):
    """The files among `files` that differ between commit `at` and the working tree."""
    out = subprocess.run(["git", "diff", "--name-only", at, "--", *files], capture_output=True, text=True, check=True)
    return out.stdout.split()


def stamp(claim_id, at):
    text = LEDGER.read_text(encoding="utf-8")
    new = re.sub(rf"(- \[{claim_id}\] .*\| checked: )\w+", rf"\g<1>{at}", text)
    LEDGER.write_text(new, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        stamp(*sys.argv[1:])
    for c in claims():
        moved = touched(c["at"], [f.strip() for f in c["files"].split(",")])
        if moved:
            print(f"[{c['id']}] in doubt, {', '.join(moved)} changed since {c['at']}\n    claim: {c['claim']}\n    leans: {c['leans']}")
