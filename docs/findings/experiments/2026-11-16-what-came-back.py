"""Counts the classes of docs/findings/2026-11-16-what-came-back.md off the log.

    python 2026-11-16-what-came-back.py <cache.json> [seconds]

The classes and the commits filed under each are read from the finding, so a class struck or a
hash moved there is counted as it then stands. A commit is told as settling or as coming back by
where the lines it removed were written, which is a `git blame` a hunk; that is some four minutes
over the whole log, so the answers are kept in the cache file and a run stops at the seconds given
(50 unless said) and says how many commits are left for the next.
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FINDING = REPO / "docs/findings/2026-11-16-what-came-back.md"
CODE = re.compile(r"^(sieve_player/|tools/|utilities/|[^/]+\.py$)")
DAY = 86400


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def lineage():
    """Every commit of v5 and the branches off it that is no merge, oldest first, each with its
    time, its branch and the lines it added and removed a file."""
    refs = [r for r in git("for-each-ref", "--format=%(refname)").split()
            if r.endswith("/v5") or "/v5-" in r]
    branch = {}
    for line in git("log", "--merges", "--first-parent", "v5", "--format=%H %P %s").splitlines():
        _, first, second, *subject = line.split()
        for c in git("rev-list", "--no-merges", second, "^" + first).split():
            branch.setdefault(c, subject[-1].split("/")[-1])
    for ref in refs:
        for c in git("rev-list", "--no-merges", ref, "^v5").split():
            branch.setdefault(c, ref.split("/")[-1])
    commits, order = {}, []
    for line in git("log", "--no-merges", "--reverse", "--format=@@@%H %ct", "--numstat", *refs).splitlines():
        if line.startswith("@@@"):
            h, t = line[3:].split()
            commits[h] = {"t": int(t), "branch": branch.get(h, "v5"), "files": {}}
            order.append(h)
        elif line.strip():
            added, removed, path = line.split("\t")
            commits[h]["files"][path] = [int(added) if added != "-" else 0, int(removed) if removed != "-" else 0]
    return order, commits


def origins(h, commits):
    """Where the lines a commit removed, or failing those the lines it added beside, were written:
    [near, far] for code, for code added beside, and for every other file. Near is the commit's own
    branch and at most a day before it."""
    me = commits[h]
    tally = {"code": [0, 0], "beside": [0, 0], "other": [0, 0]}
    for path, (added, removed) in me["files"].items():
        if " => " in path or not (added or removed):
            continue
        code = bool(CODE.match(path))
        ranges, beside = [], []
        for start, n in re.findall(r"^@@ -(\d+)(?:,(\d+))? \+", git("diff", "-U0", h + "^", h, "--", path), re.M):
            start, n = int(start), int(n or 1)
            if n:
                ranges += ["-L", f"{start},{start + n - 1}"]
            elif start:
                beside += ["-L", f"{start},{start}"]
        for which, spans in (("code" if code else "other", ranges), ("beside" if code else "other", beside)):
            if not spans or (not code and spans is beside and ranges):
                continue
            for line in git("blame", "-l", "-s", *spans, h + "^", "--", path).splitlines():
                src = commits.get(line.split()[0].lstrip("^"))
                near = src and src["branch"] == me["branch"] and me["t"] - src["t"] <= DAY
                tally[which][0 if near else 1] += 1
    return tally


def told(tally):
    for which in ("code", "beside", "other"):
        near, far = tally[which]
        if near or far:
            return "settling" if near > far else "came back"
    return "touched no earlier line"


def classes():
    """The finding's classes: id, sentence and the hashes in its section, in the order written."""
    found = []
    for section in re.split(r"^### ", FINDING.read_text(encoding="utf-8"), flags=re.M)[1:]:
        head = re.match(r"(F\d+)\. (.*)", section)
        if head:
            body = section.split("\n## ")[0]
            lists = "\n".join(l for l in body.splitlines() if l.startswith(("Came back:", "Settling:", "Touched no earlier line:", "Commits:")))
            found.append((head[1], head[2], list(dict.fromkeys(re.findall(r"`([0-9a-f]{8})`", lists)))))
    return found


def main():
    cache_path = Path(sys.argv[1])
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 50
    began = time.monotonic()
    order, commits = lineage()
    short = {h[:8]: h for h in order}
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    filed = classes()
    wanted = list(dict.fromkeys(short[h] for _, _, hashes in filed for h in hashes))
    for h in wanted:
        if h not in cache and time.monotonic() - began < budget:
            cache[h] = origins(h, commits)
    cache_path.write_text(json.dumps(cache), encoding="utf-8", newline="\n")
    left = [h for h in wanted if h not in cache]
    if left:
        sys.exit(f"{len(left)} commits left to blame; run again")

    day = lambda h: datetime.fromtimestamp(commits[h]["t"])
    kinds = {h: told(cache[h]) for h in wanted}
    count = lambda hs, kind: sum(1 for h in hs if kinds[h] == kind)
    n = len(order)
    print(f"{n} commits; {len(wanted)} filed, {100 * len(wanted) / n:.0f}%; "
          f"came back {count(wanted, 'came back')}, {100 * count(wanted, 'came back') / n:.0f}%; "
          f"settling {count(wanted, 'settling')}, {100 * count(wanted, 'settling') / n:.0f}%; "
          f"touched no earlier line {count(wanted, 'touched no earlier line')}\n")
    for cid, sentence, hashes in filed:
        hs = sorted((short[h] for h in hashes), key=order.index)
        size = lambda h: sum(a + r for a, r in commits[h]["files"].values())
        big = max(hs, key=size)
        added = sum(a for a, _ in commits[big]["files"].values())
        removed = sum(r for _, r in commits[big]["files"].values())
        landed = {}
        for h in hs:
            for path in commits[h]["files"]:
                if CODE.match(path) and " => " not in path:
                    landed[path] = landed.get(path, 0) + 1
        top = sorted(landed.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
        print(f"### {cid}. {sentence}\n")
        print(f"{len(hs)} commits: {count(hs, 'came back')} came back, {count(hs, 'settling')} settling"
              + (f", {count(hs, 'touched no earlier line')} touched no earlier line" if count(hs, 'touched no earlier line') else "")
              + f". {day(hs[0]):%m-%d} to {day(hs[-1]):%m-%d}, {(day(hs[-1]).date() - day(hs[0]).date()).days} days."
              f" Largest: `{big[:8]}`, +{added} -{removed}."
              f" Landed in: {', '.join(f'{p} {c}' for p, c in top) or 'no code'}.\n")
        for label, kind in (("Came back", "came back"), ("Settling", "settling"), ("Touched no earlier line", "touched no earlier line")):
            these = [h for h in hs if kinds[h] == kind]
            if these:
                print(f"{label}: " + " ".join(f"`{h[:8]}`" for h in these) + "\n")


main()
